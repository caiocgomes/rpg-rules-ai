import asyncio

from langchain_openai import ChatOpenAI

from caprag.config import settings
from caprag.prompts import get_multi_question_prompt
from caprag.retriever import get_retriever
from caprag.schemas import LLMQuestions, Question, Questions, State
from caprag.strategies.base import RetrievalStrategy


class MultiQuestionStrategy(RetrievalStrategy):
    async def execute(self, state: State) -> dict:
        llm = ChatOpenAI(model=settings.llm_model, temperature=0)
        prompt = get_multi_question_prompt()
        chain = prompt | llm.with_structured_output(LLMQuestions)

        main_question = state["messages"][-1].content
        llm_result = await chain.ainvoke(
            {"messages": [("user", f"Expand the following question: {state['messages']}")]}
        )
        questions = Questions(
            questions=[Question(question=q.question) for q in llm_result.questions]
        )
        questions.questions.append(Question(question=main_question))

        retriever = get_retriever()

        async def process_question(question):
            question.context = await retriever.ainvoke(question.question)

        await asyncio.gather(*[process_question(q) for q in questions.questions])

        return {"questions": questions, "main_question": main_question}
