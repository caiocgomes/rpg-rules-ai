import json
import os

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from caprag.config import settings
from caprag.prompts import get_rag_prompt
from caprag.schemas import AnswerWithSources, State
from caprag.strategies import get_strategy


def _setup_langsmith():
    if settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project


def _get_llm():
    return ChatOpenAI(model=settings.llm_model, temperature=0)


async def retrieve_with_strategy(state: State):
    strategy = get_strategy()
    return await strategy.execute(state)


async def generate(state: State):
    llm = _get_llm()
    prompt = get_rag_prompt()

    seen = set()
    blocks = []
    idx = 1
    for question in state["questions"].questions:
        for doc in question.context:
            key = (doc.metadata.get("book", ""), doc.page_content)
            if key in seen:
                continue
            seen.add(key)
            blocks.append(
                f"[{idx}] Source: {doc.metadata['book']}\n{doc.page_content}"
            )
            idx += 1
    docs_content = "\n---\n".join(blocks)

    messages = await prompt.ainvoke(
        {"question": state["main_question"], "context": docs_content}
    )
    structured_llm = llm.with_structured_output(AnswerWithSources)
    response = await structured_llm.ainvoke(messages)

    return {"answer": response, "messages": [AIMessage(content=json.dumps(response))]}


def build_graph():
    _setup_langsmith()

    graph_builder = StateGraph(State)
    graph_builder.add_node("retrieve", retrieve_with_strategy)
    graph_builder.add_node("generate", generate)
    graph_builder.add_edge(START, "retrieve")
    graph_builder.add_edge("retrieve", "generate")
    graph_builder.add_edge("generate", END)

    return graph_builder.compile()
