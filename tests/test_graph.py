import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from caprag.graph import (
    _enrich_citations_with_context,
    _find_best_substring,
    _ground_citations,
    _validate_citations,
)
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
        "answer": "GURPS uses 3d6 for resolution [1].",
        "sources": ["GURPS Basic"],
        "citations": [{"index": 1, "quote": "GURPS uses 3d6.", "source": "GURPS Basic"}],
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

    assert result["answer"]["answer"] == answer["answer"]
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)

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
        "answer": "Rule A applies [1]. Rule B expands [2]. Rule C adds [3].",
        "sources": ["Book1", "Book2", "Book3"],
        "citations": [
            {"index": 1, "quote": "Rule A.", "source": "Book1"},
            {"index": 2, "quote": "Rule B.", "source": "Book2"},
            {"index": 3, "quote": "Rule C.", "source": "Book3"},
        ],
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
    assert result["answer"]["answer"] == answer["answer"]


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
    assert result["answer"]["answer"] == answer["answer"]


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
        "answer": "Same rule applies [1] and different rule too [2].",
        "sources": ["BookA", "BookB"],
        "citations": [
            {"index": 1, "quote": "Same rule.", "source": "BookA"},
            {"index": 2, "quote": "Different rule.", "source": "BookB"},
        ],
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


@pytest.mark.asyncio
@patch("caprag.graph.get_rag_prompt")
@patch("caprag.graph._get_llm")
async def test_generate_retries_on_missing_citations(mock_get_llm, mock_get_prompt):
    """When LLM returns no citations with context available, retry once."""
    doc = Document(page_content="GURPS uses 3d6.", metadata={"book": "GURPS Basic"})
    questions = Questions(
        questions=[Question(question="How?", context=[doc])]
    )

    no_citations: AnswerWithSources = {
        "answer": "GURPS uses 3d6.",
        "sources": ["GURPS Basic"],
        "citations": [],
        "see_also": [],
    }
    with_citations: AnswerWithSources = {
        "answer": "GURPS uses 3d6 [1].",
        "sources": ["GURPS Basic"],
        "citations": [{"index": 1, "quote": "GURPS uses 3d6.", "source": "GURPS Basic"}],
        "see_also": [],
    }

    mock_prompt = MagicMock()
    mock_prompt.ainvoke = AsyncMock(return_value=MagicMock(messages=[]))
    mock_get_prompt.return_value = mock_prompt

    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(side_effect=[no_citations, with_citations])

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    state = {"main_question": "How?", "questions": questions, "messages": []}

    from caprag.graph import generate

    result = await generate(state)

    assert mock_structured.ainvoke.await_count == 2
    assert len(result["answer"]["citations"]) == 1
    assert "[1]" in result["answer"]["answer"]


@pytest.mark.asyncio
@patch("caprag.graph.get_rag_prompt")
@patch("caprag.graph._get_llm")
async def test_generate_fallback_on_persistent_missing_citations(
    mock_get_llm, mock_get_prompt
):
    """When retry also fails, return fallback response."""
    doc = Document(page_content="Some rule.", metadata={"book": "Book"})
    questions = Questions(
        questions=[Question(question="Q?", context=[doc])]
    )

    no_citations: AnswerWithSources = {
        "answer": "Answer without markers.",
        "sources": ["Book"],
        "citations": [],
        "see_also": [],
    }

    mock_prompt = MagicMock()
    mock_prompt.ainvoke = AsyncMock(return_value=MagicMock(messages=[]))
    mock_get_prompt.return_value = mock_prompt

    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=no_citations)

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    state = {"main_question": "Q?", "questions": questions, "messages": []}

    from caprag.graph import generate

    result = await generate(state)

    assert mock_structured.ainvoke.await_count == 2
    assert "could not produce" in result["answer"]["answer"]
    assert result["answer"]["citations"] == []


# ---------------------------------------------------------------------------
# _validate_citations
# ---------------------------------------------------------------------------


def test_validate_citations_happy_path():
    response: AnswerWithSources = {
        "answer": "Rapid Strike allows two attacks [1]. Martial Arts expands this [2].",
        "sources": ["GURPS Basic", "GURPS Martial Arts"],
        "citations": [
            {"index": 1, "quote": "Make two attacks", "source": "GURPS Basic"},
            {"index": 2, "quote": "Expanded options", "source": "GURPS Martial Arts"},
        ],
        "see_also": [],
    }
    result = _validate_citations(response)
    assert result["answer"] == response["answer"]
    assert len(result["citations"]) == 2
    assert result["citations"][0]["index"] == 1
    assert result["citations"][1]["index"] == 2


def test_validate_citations_orphan_citations_removed():
    response: AnswerWithSources = {
        "answer": "Only one claim here [1].",
        "sources": ["Book1", "Book2"],
        "citations": [
            {"index": 1, "quote": "Claim one", "source": "Book1"},
            {"index": 3, "quote": "Orphan", "source": "Book2"},
        ],
        "see_also": [],
    }
    result = _validate_citations(response)
    assert len(result["citations"]) == 1
    assert result["citations"][0]["index"] == 1
    # Sources should only include books with surviving citations
    assert result["sources"] == ["Book1"]


def test_validate_citations_sources_derived_from_citations():
    """LLM lists two books in sources but only cites one — sources should shrink."""
    response: AnswerWithSources = {
        "answer": "The base rule is clear [1]. Advanced rules expand on it [2].",
        "sources": ["GURPS Basic", "GURPS Martial Arts"],
        "citations": [
            {"index": 1, "quote": "Base rule", "source": "GURPS Basic"},
            {"index": 2, "quote": "Advanced rule", "source": "GURPS Basic"},
        ],
        "see_also": [],
    }
    result = _validate_citations(response)
    assert result["sources"] == ["GURPS Basic"]
    assert "GURPS Martial Arts" not in result["sources"]


def test_validate_citations_orphan_markers_cleaned():
    response: AnswerWithSources = {
        "answer": "Claim one [1]. Ghost reference [99].",
        "sources": ["Book1"],
        "citations": [
            {"index": 1, "quote": "Claim one", "source": "Book1"},
        ],
        "see_also": [],
    }
    result = _validate_citations(response)
    assert "[99]" not in result["answer"]
    assert "[1]" in result["answer"]
    assert len(result["citations"]) == 1


def test_validate_citations_no_markers_passthrough():
    response: AnswerWithSources = {
        "answer": "Plain answer with no markers.",
        "sources": ["Book1"],
        "citations": [
            {"index": 1, "quote": "Some quote", "source": "Book1"},
        ],
        "see_also": [],
    }
    result = _validate_citations(response)
    assert result["answer"] == "Plain answer with no markers."
    assert result["citations"] == response["citations"]


def test_validate_citations_empty_citations():
    response: AnswerWithSources = {
        "answer": "No info available.",
        "sources": [],
        "citations": [],
        "see_also": [],
    }
    result = _validate_citations(response)
    assert result["answer"] == "No info available."
    assert result["citations"] == []


# ---------------------------------------------------------------------------
# _find_best_substring
# ---------------------------------------------------------------------------


def test_find_best_substring_exact_match():
    haystack = "Rapid Strike allows you to make two melee attacks per turn at -6 each."
    needle = "two melee attacks per turn at -6 each"
    result = _find_best_substring(needle, haystack)
    assert result == "two melee attacks per turn at -6 each"


def test_find_best_substring_case_insensitive():
    haystack = "The DX penalty is -4 for this maneuver."
    needle = "the dx penalty is -4"
    result = _find_best_substring(needle, haystack)
    assert result is not None
    assert result.lower() == "the dx penalty is -4"


def test_find_best_substring_paraphrased():
    haystack = "Rapid Strike allows the character to make two melee attacks in a single turn, each at -6 to skill."
    needle = "Rapid Strike lets a character make two melee attacks in one turn, each at -6 to skill."
    result = _find_best_substring(needle, haystack)
    assert result is not None
    # Should return the actual text from haystack, not the needle
    assert result in haystack


def test_find_best_substring_no_match():
    haystack = "This passage is about cooking recipes."
    needle = "Rapid Strike allows two attacks at -6 each."
    result = _find_best_substring(needle, haystack)
    assert result is None


def test_find_best_substring_empty_inputs():
    assert _find_best_substring("", "some text") is None
    assert _find_best_substring("needle", "") is None
    assert _find_best_substring("", "") is None


# ---------------------------------------------------------------------------
# _ground_citations
# ---------------------------------------------------------------------------


def test_ground_citations_replaces_paraphrased_quote():
    original_text = "Rapid Strike (p. B370) allows you to make two melee attacks per turn, each at -6 to skill."
    response = {
        "answer": "Rapid Strike gives two attacks at -6 [1].",
        "sources": ["GURPS Basic"],
        "citations": [
            {
                "index": 1,
                "quote": "Rapid Strike allows you to make two melee attacks per turn each at -6 to skill",
                "source": "GURPS Basic",
            }
        ],
        "see_also": [],
    }
    context_map = {1: original_text}
    result = _ground_citations(response, context_map)
    # The quote should now be from the original text
    assert result["citations"][0]["quote"] in original_text


def test_ground_citations_preserves_exact_quote():
    original_text = "DX-based skill. Defaults: DX-5 or Karate-4."
    response = {
        "answer": "It defaults to DX-5 [1].",
        "sources": ["Book"],
        "citations": [
            {"index": 1, "quote": "Defaults: DX-5 or Karate-4.", "source": "Book"}
        ],
        "see_also": [],
    }
    context_map = {1: original_text}
    result = _ground_citations(response, context_map)
    assert result["citations"][0]["quote"] == "Defaults: DX-5 or Karate-4."


def test_ground_citations_no_context_map():
    response = {
        "answer": "Answer [1].",
        "sources": ["Book"],
        "citations": [{"index": 1, "quote": "some quote", "source": "Book"}],
        "see_also": [],
    }
    result = _ground_citations(response, {})
    assert result["citations"][0]["quote"] == "some quote"


def test_ground_citations_missing_index_in_map():
    response = {
        "answer": "Answer [1] and [2].",
        "sources": ["Book"],
        "citations": [
            {"index": 1, "quote": "quote one", "source": "Book"},
            {"index": 2, "quote": "quote two", "source": "Book"},
        ],
        "see_also": [],
    }
    context_map = {1: "The actual text for quote one is here."}
    result = _ground_citations(response, context_map)
    # Index 1 should be grounded, index 2 should be unchanged
    assert result["citations"][0]["quote"] in "The actual text for quote one is here."
    assert result["citations"][1]["quote"] == "quote two"


def test_ground_citations_empty_citations():
    response = {
        "answer": "No citations.",
        "sources": [],
        "citations": [],
        "see_also": [],
    }
    result = _ground_citations(response, {1: "text"})
    assert result["citations"] == []


# ---------------------------------------------------------------------------
# _enrich_citations_with_context
# ---------------------------------------------------------------------------


def test_enrich_citations_quote_found():
    response = {
        "answer": "Answer [1].",
        "sources": ["Book"],
        "citations": [
            {"index": 1, "quote": "two attacks at -6", "source": "Book"}
        ],
        "see_also": [],
    }
    context_map = {1: "Rapid Strike allows two attacks at -6 each turn."}
    result = _enrich_citations_with_context(response, context_map)
    html = result["citations"][0]["context_html"]
    assert "<mark>" in html
    assert "two attacks at -6" in html
    assert "Rapid Strike allows" in html


def test_enrich_citations_quote_not_found():
    response = {
        "answer": "Answer [1].",
        "sources": ["Book"],
        "citations": [
            {"index": 1, "quote": "completely different text", "source": "Book"}
        ],
        "see_also": [],
    }
    context_map = {1: "Rapid Strike allows two attacks at -6 each turn."}
    result = _enrich_citations_with_context(response, context_map)
    html = result["citations"][0]["context_html"]
    assert "<mark>" not in html
    assert "Rapid Strike" in html


def test_enrich_citations_no_context_map():
    response = {
        "answer": "Answer [1].",
        "sources": ["Book"],
        "citations": [
            {"index": 1, "quote": "some quote", "source": "Book"}
        ],
        "see_also": [],
    }
    result = _enrich_citations_with_context(response, {})
    assert "context_html" not in result["citations"][0]


def test_enrich_citations_html_escapes_special_chars():
    response = {
        "answer": "Answer [1].",
        "sources": ["Book"],
        "citations": [
            {"index": 1, "quote": "damage < 10", "source": "Book"}
        ],
        "see_also": [],
    }
    context_map = {1: "If damage < 10 & HP > 0, the character survives."}
    result = _enrich_citations_with_context(response, context_map)
    html = result["citations"][0]["context_html"]
    assert "&lt;" in html
    assert "&amp;" in html
    assert "<mark>" in html


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
