from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from rpg_rules_ai.schemas import Question, Questions
from rpg_rules_ai.strategies.multi_question import MultiQuestionStrategy


def _make_state(question: str) -> dict:
    msg = MagicMock()
    msg.content = question
    return {"messages": [msg]}


@pytest.mark.asyncio
async def test_execute_happy_path():
    strategy = MultiQuestionStrategy()
    expanded = Questions(questions=[Question(question="Sub-question 1")])
    docs = [Document(page_content="Some rule", metadata={"book": "Basic Set"})]

    with (
        patch("rpg_rules_ai.strategies.multi_question.get_multi_question_prompt") as mock_prompt,
        patch("rpg_rules_ai.strategies.multi_question.get_retriever") as mock_retriever,
        patch("rpg_rules_ai.strategies.multi_question.ChatOpenAI") as mock_llm_cls,
    ):
        # Setup chain: prompt | llm.with_structured_output(Questions)
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=expanded)
        mock_prompt_instance = MagicMock()
        mock_prompt.return_value = mock_prompt_instance
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(return_value=MagicMock())
        mock_llm_cls.return_value = mock_llm
        mock_prompt_instance.__or__ = MagicMock(return_value=mock_chain)

        # Setup retriever
        mock_ret = AsyncMock()
        mock_ret.ainvoke = AsyncMock(return_value=docs)
        mock_retriever.return_value = mock_ret

        state = _make_state("How does Magery work?")
        result = await strategy.execute(state)

        assert result["main_question"] == "How does Magery work?"
        questions = result["questions"]
        # Original question should be appended
        question_texts = [q.question for q in questions.questions]
        assert "How does Magery work?" in question_texts
        # Retriever called for each question (expanded + original)
        assert mock_ret.ainvoke.call_count == len(questions.questions)
        # Context assigned to each question
        for q in questions.questions:
            assert q.context == docs
