import asyncio
import hashlib
from typing import List

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from caprag.config import settings
from caprag.prompts import get_multi_question_prompt
from caprag.retriever import get_retriever
from caprag.schemas import LLMQuestions, Question, Questions, State
from caprag.strategies.base import RetrievalStrategy

MAX_HOPS = 3


class SufficiencyAnalysis(BaseModel):
    sufficient: bool = Field(
        description="Whether the retrieved context is sufficient to answer the question"
    )
    new_queries: List[str] = Field(
        default_factory=list,
        description="New queries to search for if context is not sufficient",
    )
    reasoning: str = Field(
        description="Brief explanation of why context is or isn't sufficient"
    )


ANALYZER_PROMPT = """You are analyzing whether retrieved documents contain enough context to answer a question about RPG rules (GURPS, etc.).

## Original Question
{question}

## Retrieved Documents So Far
{context}

## Task
Analyze whether the retrieved documents provide sufficient context to fully answer the question.

Pay special attention to:
- Cross-references to other books or sections (e.g., "see Powers, p. 100", "modified by Rapid Strike")
- Rules that interact with other rules mentioned but not yet retrieved
- Missing mechanical details (costs, modifiers, prerequisites) that are referenced but not present

If the context is NOT sufficient, generate specific queries to find the missing information.
If the context IS sufficient, confirm and explain why."""


def _doc_hash(doc: Document) -> str:
    book = doc.metadata.get("book", "")
    return hashlib.md5(f"{book}:{doc.page_content}".encode()).hexdigest()


def _deduplicate(existing: List[Document], new: List[Document]) -> List[Document]:
    seen = {_doc_hash(d) for d in existing}
    result = []
    for doc in new:
        h = _doc_hash(doc)
        if h not in seen:
            seen.add(h)
            result.append(doc)
    return result


class MultiHopStrategy(RetrievalStrategy):
    async def execute(self, state: State) -> dict:
        llm = ChatOpenAI(model=settings.llm_model, temperature=0)
        retriever = get_retriever()
        main_question = state["messages"][-1].content

        # Initial query expansion (same as multi-question)
        prompt = get_multi_question_prompt()
        chain = prompt | llm.with_structured_output(LLMQuestions)
        llm_result = await chain.ainvoke(
            {"messages": [("user", f"Expand the following question: {state['messages']}")]}
        )
        questions = Questions(
            questions=[Question(question=q.question) for q in llm_result.questions]
        )
        questions.questions.append(Question(question=main_question))

        # Hop 1: retrieve for all initial queries
        all_docs: List[Document] = []
        await self._retrieve_batch(retriever, questions.questions, all_docs)

        # Iterative hops
        analyzer = llm.with_structured_output(SufficiencyAnalysis)
        for hop in range(MAX_HOPS - 1):  # -1 because we already did hop 1
            context_text = self._format_context(all_docs)
            analysis = await analyzer.ainvoke(
                ANALYZER_PROMPT.format(question=main_question, context=context_text)
            )

            if analysis.sufficient or not analysis.new_queries:
                break

            new_questions = [Question(question=q) for q in analysis.new_queries]
            await self._retrieve_batch(retriever, new_questions, all_docs)
            questions.questions.extend(new_questions)

        # TODO: refactor to keep per-question doc association instead of dumping
        # all docs into questions[0].context. This would enable showing which
        # sub-question each citation came from.
        for q in questions.questions:
            if not q.context:
                q.context = []
        questions.questions[0].context = all_docs

        return {"questions": questions, "main_question": main_question}

    async def _retrieve_batch(
        self,
        retriever,
        questions: List[Question],
        accumulated: List[Document],
    ):
        async def fetch(q: Question):
            return await retriever.ainvoke(q.question)

        results = await asyncio.gather(*[fetch(q) for q in questions])
        for docs in results:
            new_docs = _deduplicate(accumulated, docs)
            accumulated.extend(new_docs)

    def _format_context(self, docs: List[Document]) -> str:
        return "\n\n".join(
            f"[{doc.metadata.get('book', 'Unknown')}]\n{doc.page_content}"
            for doc in docs
        )
