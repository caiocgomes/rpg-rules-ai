import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from caprag.schemas import AnswerWithSources, Question, Questions, State


# ---------------------------------------------------------------------------
# _setup_langsmith
# ---------------------------------------------------------------------------


@patch("caprag.graph.settings")
def test_setup_langsmith_with_key(mock_settings):
    mock_settings.langsmith_api_key = "sk-test-123"
    mock_settings.langchain_project = "test-project"

    from caprag.graph import _setup_langsmith

    _setup_langsmith()

    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGCHAIN_ENDPOINT"] == "https://api.smith.langchain.com"
    assert os.environ["LANGCHAIN_API_KEY"] == "sk-test-123"
    assert os.environ["LANGCHAIN_PROJECT"] == "test-project"


@patch("caprag.graph.settings")
def test_setup_langsmith_without_key(mock_settings):
    mock_settings.langsmith_api_key = ""

    # Clear env vars that might have been set by the previous test
    for key in [
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_ENDPOINT",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_PROJECT",
    ]:
        os.environ.pop(key, None)

    from caprag.graph import _setup_langsmith

    _setup_langsmith()

    assert "LANGCHAIN_API_KEY" not in os.environ


# ---------------------------------------------------------------------------
# _get_llm
# ---------------------------------------------------------------------------


@patch("caprag.graph.settings")
@patch("caprag.graph.ChatOpenAI")
def test_get_llm(mock_chat, mock_settings):
    mock_settings.llm_model = "gpt-4o-mini"
    sentinel = MagicMock()
    mock_chat.return_value = sentinel

    from caprag.graph import _get_llm

    result = _get_llm()

    mock_chat.assert_called_once_with(model="gpt-4o-mini", temperature=0)
    assert result is sentinel


# ---------------------------------------------------------------------------
# retrieve_with_strategy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("caprag.graph.get_strategy")
async def test_retrieve_with_strategy(mock_get_strategy):
    mock_strategy = MagicMock()
    expected = {"questions": Questions(questions=[])}
    mock_strategy.execute = AsyncMock(return_value=expected)
    mock_get_strategy.return_value = mock_strategy

    fake_state = {"main_question": "What is GURPS?", "messages": []}

    from caprag.graph import retrieve_with_strategy

    result = await retrieve_with_strategy(fake_state)

    mock_get_strategy.assert_called_once()
    mock_strategy.execute.assert_awaited_once_with(fake_state)
    assert result is expected


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("caprag.graph.get_rag_prompt")
@patch("caprag.graph._get_llm")
async def test_generate_single_question_single_doc(mock_get_llm, mock_get_prompt):
    doc = Document(page_content="GURPS uses 3d6.", metadata={"book": "GURPS Basic"})
    questions = Questions(
        questions=[Question(question="How does GURPS work?", context=[doc])]
    )

    answer: AnswerWithSources = {
        "answer": "GURPS uses 3d6 for resolution.",
        "sources": ["GURPS Basic"],
        "citations": [{"quote": "GURPS uses 3d6.", "source": "GURPS Basic"}],
        "see_also": ["Dice Rolls"],
    }

    mock_prompt = MagicMock()
    mock_prompt.ainvoke = AsyncMock(return_value="formatted-messages")
    mock_get_prompt.return_value = mock_prompt

    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=answer)

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    state = {
        "main_question": "How does GURPS work?",
        "questions": questions,
        "messages": [],
    }

    from caprag.graph import generate

    result = await generate(state)

    assert result["answer"] is answer
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    assert json.loads(result["messages"][0].content) == answer

    mock_prompt.ainvoke.assert_awaited_once()
    call_kwargs = mock_prompt.ainvoke.call_args[0][0]
    assert call_kwargs["question"] == "How does GURPS work?"
    assert "GURPS uses 3d6." in call_kwargs["context"]
    assert "Source: GURPS Basic" in call_kwargs["context"]

    mock_llm.with_structured_output.assert_called_once_with(AnswerWithSources)
    mock_structured.ainvoke.assert_awaited_once_with("formatted-messages")


@pytest.mark.asyncio
@patch("caprag.graph.get_rag_prompt")
@patch("caprag.graph._get_llm")
async def test_generate_multiple_questions_multiple_docs(
    mock_get_llm, mock_get_prompt
):
    doc1 = Document(page_content="Rule A.", metadata={"book": "Book1"})
    doc2 = Document(page_content="Rule B.", metadata={"book": "Book2"})
    doc3 = Document(page_content="Rule C.", metadata={"book": "Book3"})

    questions = Questions(
        questions=[
            Question(question="Q1", context=[doc1, doc2]),
            Question(question="Q2", context=[doc3]),
        ]
    )

    answer: AnswerWithSources = {
        "answer": "Combined answer.",
        "sources": ["Book1", "Book2", "Book3"],
        "citations": [],
        "see_also": [],
    }

    mock_prompt = MagicMock()
    mock_prompt.ainvoke = AsyncMock(return_value="msgs")
    mock_get_prompt.return_value = mock_prompt

    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=answer)

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    state = {
        "main_question": "Complex question",
        "questions": questions,
        "messages": [],
    }

    from caprag.graph import generate

    result = await generate(state)

    call_kwargs = mock_prompt.ainvoke.call_args[0][0]
    context = call_kwargs["context"]
    assert "Rule A." in context
    assert "Source: Book1" in context
    assert "Rule B." in context
    assert "Source: Book2" in context
    assert "Rule C." in context
    assert "Source: Book3" in context
    # Verify numbered format with separators
    assert "[1] Source: Book1" in context
    assert "[2] Source: Book2" in context
    assert "[3] Source: Book3" in context
    assert "---" in context
    assert result["answer"] is answer


@pytest.mark.asyncio
@patch("caprag.graph.get_rag_prompt")
@patch("caprag.graph._get_llm")
async def test_generate_empty_context(mock_get_llm, mock_get_prompt):
    questions = Questions(
        questions=[Question(question="Q1", context=[])]
    )

    answer: AnswerWithSources = {
        "answer": "No info.",
        "sources": [],
        "citations": [],
        "see_also": [],
    }

    mock_prompt = MagicMock()
    mock_prompt.ainvoke = AsyncMock(return_value="msgs")
    mock_get_prompt.return_value = mock_prompt

    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=answer)

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    state = {
        "main_question": "Unknown question",
        "questions": questions,
        "messages": [],
    }

    from caprag.graph import generate

    result = await generate(state)

    call_kwargs = mock_prompt.ainvoke.call_args[0][0]
    assert call_kwargs["context"] == ""
    assert result["answer"] is answer


@pytest.mark.asyncio
@patch("caprag.graph.get_rag_prompt")
@patch("caprag.graph._get_llm")
async def test_generate_deduplicates_docs(mock_get_llm, mock_get_prompt):
    doc1 = Document(page_content="Same rule.", metadata={"book": "BookA"})
    doc1_dup = Document(page_content="Same rule.", metadata={"book": "BookA"})
    doc2 = Document(page_content="Different rule.", metadata={"book": "BookB"})

    questions = Questions(
        questions=[
            Question(question="Q1", context=[doc1, doc1_dup, doc2]),
        ]
    )

    answer: AnswerWithSources = {
        "answer": "Answer.",
        "sources": ["BookA", "BookB"],
        "citations": [],
        "see_also": [],
    }

    mock_prompt = MagicMock()
    mock_prompt.ainvoke = AsyncMock(return_value="msgs")
    mock_get_prompt.return_value = mock_prompt

    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=answer)

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    state = {
        "main_question": "Dedup test",
        "questions": questions,
        "messages": [],
    }

    from caprag.graph import generate

    result = await generate(state)

    context = mock_prompt.ainvoke.call_args[0][0]["context"]
    # Should have [1] and [2] but not [3] (duplicate removed)
    assert "[1] Source: BookA" in context
    assert "[2] Source: BookB" in context
    assert "[3]" not in context


# ---------------------------------------------------------------------------
# build_graph
# ---------------------------------------------------------------------------


@patch("caprag.graph._setup_langsmith")
def test_build_graph_returns_compiled_graph(mock_setup):
    from caprag.graph import build_graph

    graph = build_graph()

    mock_setup.assert_called_once()

    # The compiled graph should have the nodes we defined
    node_names = set(graph.get_graph().nodes.keys())
    assert "retrieve" in node_names
    assert "generate" in node_names

    # Verify it's a runnable (compiled graph)
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "ainvoke")
