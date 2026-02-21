import asyncio
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from rpg_rules_ai.schemas import Question, Questions, State
from rpg_rules_ai.strategies.base import RetrievalStrategy
from rpg_rules_ai.strategies.multi_hop import (
    MultiHopStrategy,
    SufficiencyAnalysis,
    _deduplicate,
    _doc_hash,
)
from rpg_rules_ai.strategies.multi_question import MultiQuestionStrategy


# --- Base interface tests ---


def test_strategy_abc_cannot_instantiate():
    with pytest.raises(TypeError):
        RetrievalStrategy()


def test_strategy_subclass_must_implement_execute():
    class BadStrategy(RetrievalStrategy):
        pass

    with pytest.raises(TypeError):
        BadStrategy()


def test_strategy_subclass_with_execute_works():
    class GoodStrategy(RetrievalStrategy):
        async def execute(self, state):
            return state

    s = GoodStrategy()
    assert s is not None


# --- Config validation tests ---


def test_config_valid_strategies():
    from pydantic import ValidationError

    from rpg_rules_ai.config import Settings

    s = Settings(openai_api_key="test", retrieval_strategy="multi-hop")
    assert s.retrieval_strategy == "multi-hop"

    s = Settings(openai_api_key="test", retrieval_strategy="multi-question")
    assert s.retrieval_strategy == "multi-question"


def test_config_invalid_strategy():
    from pydantic import ValidationError

    from rpg_rules_ai.config import Settings

    with pytest.raises(ValidationError):
        Settings(openai_api_key="test", retrieval_strategy="invalid")


# --- Deduplication tests ---


def _make_doc(content: str, book: str = "Basic Set") -> Document:
    return Document(page_content=content, metadata={"book": book})


def test_doc_hash_same_content_same_book():
    d1 = _make_doc("Magery costs 5 points per level", "Basic Set")
    d2 = _make_doc("Magery costs 5 points per level", "Basic Set")
    assert _doc_hash(d1) == _doc_hash(d2)


def test_doc_hash_same_content_different_book():
    d1 = _make_doc("Combat rules", "Basic Set")
    d2 = _make_doc("Combat rules", "Martial Arts")
    assert _doc_hash(d1) != _doc_hash(d2)


def test_deduplicate_removes_duplicates():
    existing = [_make_doc("A", "Book1"), _make_doc("B", "Book1")]
    new = [_make_doc("A", "Book1"), _make_doc("C", "Book2")]
    result = _deduplicate(existing, new)
    assert len(result) == 1
    assert result[0].page_content == "C"


def test_deduplicate_empty_existing():
    new = [_make_doc("A", "Book1"), _make_doc("B", "Book2")]
    result = _deduplicate([], new)
    assert len(result) == 2


def test_deduplicate_all_duplicates():
    existing = [_make_doc("A", "Book1")]
    new = [_make_doc("A", "Book1")]
    result = _deduplicate(existing, new)
    assert len(result) == 0


# --- MultiHopStrategy loop tests ---


def _make_state(question: str) -> dict:
    msg = MagicMock()
    msg.content = question
    return {"messages": [msg], "main_question": question}


@pytest.mark.asyncio
async def test_multi_hop_single_hop_sufficient():
    strategy = MultiHopStrategy()
    docs = [_make_doc("Magery costs 5 points per level.", "Basic Set")]

    mock_questions = Questions(questions=[Question(question="What is Magery?")])
    mock_analysis = SufficiencyAnalysis(
        sufficient=True, new_queries=[], reasoning="Context covers the question"
    )

    with (
        patch("rpg_rules_ai.strategies.multi_hop.get_multi_question_prompt") as mock_prompt,
        patch("rpg_rules_ai.strategies.multi_hop.get_retriever") as mock_retriever,
        patch("rpg_rules_ai.strategies.multi_hop.ChatOpenAI") as mock_llm_cls,
    ):
        # Setup multi-question chain
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_questions)
        mock_prompt_instance = MagicMock()
        mock_prompt.return_value = mock_prompt_instance
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock()

        # First call to with_structured_output returns the chain for Questions
        # Second call returns the analyzer
        mock_analyzer = AsyncMock()
        mock_analyzer.ainvoke = AsyncMock(return_value=mock_analysis)

        call_count = 0
        def structured_output_side_effect(schema):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock()  # For Questions chain
            return mock_analyzer

        mock_llm.with_structured_output = MagicMock(side_effect=structured_output_side_effect)
        mock_llm_cls.return_value = mock_llm

        # Make prompt | llm.with_structured_output(...) work
        mock_prompt_instance.__or__ = MagicMock(return_value=mock_chain)

        # Setup retriever
        mock_ret = AsyncMock()
        mock_ret.ainvoke = AsyncMock(return_value=docs)
        mock_retriever.return_value = mock_ret

        state = _make_state("What is Magery?")
        result = await strategy.execute(state)

        assert result["main_question"] == "What is Magery?"
        assert result["questions"] is not None
        # Analyzer should have been called once and returned sufficient=True
        mock_analyzer.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_multi_hop_respects_max_hops():
    strategy = MultiHopStrategy()
    docs = [_make_doc("Some partial info", "Basic Set")]

    mock_questions = Questions(questions=[Question(question="Complex question")])
    mock_analysis = SufficiencyAnalysis(
        sufficient=False,
        new_queries=["more info needed"],
        reasoning="Missing cross-references",
    )

    with (
        patch("rpg_rules_ai.strategies.multi_hop.get_multi_question_prompt") as mock_prompt,
        patch("rpg_rules_ai.strategies.multi_hop.get_retriever") as mock_retriever,
        patch("rpg_rules_ai.strategies.multi_hop.ChatOpenAI") as mock_llm_cls,
    ):
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_questions)
        mock_prompt_instance = MagicMock()
        mock_prompt.return_value = mock_prompt_instance

        mock_analyzer = AsyncMock()
        mock_analyzer.ainvoke = AsyncMock(return_value=mock_analysis)

        call_count = 0
        def structured_output_side_effect(schema):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock()
            return mock_analyzer

        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(side_effect=structured_output_side_effect)
        mock_llm_cls.return_value = mock_llm
        mock_prompt_instance.__or__ = MagicMock(return_value=mock_chain)

        mock_ret = AsyncMock()
        mock_ret.ainvoke = AsyncMock(return_value=docs)
        mock_retriever.return_value = mock_ret

        state = _make_state("Complex cross-book question")
        result = await strategy.execute(state)

        # MAX_HOPS is 3, first hop + 2 more iterations = analyzer called 2 times
        assert mock_analyzer.ainvoke.call_count == 2
