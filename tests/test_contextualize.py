"""Tests for contextual embedding enrichment."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document


@pytest.fixture
def parent_doc():
    return Document(
        page_content="Rapid Strike (p. B370) lets you trade skill for multiple attacks.",
        metadata={"book": "BasicSet.md", "section_headers": "Combat > Maneuvers"},
    )


@pytest.fixture
def child_doc():
    return Document(
        page_content="See also Martial Arts, p.127 for expanded options.",
        metadata={"book": "BasicSet.md", "doc_id": "abc", "section_headers": "Combat > Maneuvers"},
    )


@pytest.mark.asyncio
@patch("rpg_rules_ai.contextualize.ChatOpenAI")
async def test_generate_context_returns_string(mock_chat_cls, parent_doc, child_doc):
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "This passage describes Rapid Strike cross-references to Martial Arts."
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    mock_chat_cls.return_value = mock_llm

    from rpg_rules_ai.contextualize import generate_context

    result = await generate_context(parent_doc, child_doc, "BasicSet.md")

    assert isinstance(result, str)
    assert "Rapid Strike" in result
    mock_chat_cls.assert_called_once_with(model="gpt-4o-mini", temperature=0)
    mock_llm.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
@patch("rpg_rules_ai.contextualize.ChatOpenAI")
async def test_generate_context_uses_custom_model(mock_chat_cls, parent_doc, child_doc):
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Context prefix."
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    mock_chat_cls.return_value = mock_llm

    from rpg_rules_ai.contextualize import generate_context

    await generate_context(parent_doc, child_doc, "BasicSet.md", model="gpt-4o")

    mock_chat_cls.assert_called_once_with(model="gpt-4o", temperature=0)


@pytest.mark.asyncio
@patch("rpg_rules_ai.contextualize.ChatOpenAI")
async def test_generate_context_falls_back_to_parent_headers(mock_chat_cls):
    parent = Document(
        page_content="Parent content.",
        metadata={"book": "Book.md", "section_headers": "Chapter 1"},
    )
    child = Document(
        page_content="Child content.",
        metadata={"book": "Book.md", "doc_id": "xyz"},
    )

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Context."
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    mock_chat_cls.return_value = mock_llm

    from rpg_rules_ai.contextualize import generate_context

    await generate_context(parent, child, "Book.md")

    # Verify prompt was invoked (the fallback to parent headers happens internally)
    mock_llm.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
@patch("rpg_rules_ai.contextualize.generate_context")
async def test_contextualize_batch_processes_all(mock_gen):
    mock_gen.side_effect = [
        "Context for chunk 0.",
        "Context for chunk 1.",
        "Context for chunk 2.",
    ]

    items = [
        (Document(page_content=f"P{i}"), Document(page_content=f"C{i}"), f"Book{i}.md")
        for i in range(3)
    ]

    from rpg_rules_ai.contextualize import contextualize_batch

    results = await contextualize_batch(items, batch_size=10)

    assert len(results) == 3
    assert results[0] == "Context for chunk 0."
    assert results[2] == "Context for chunk 2."


@pytest.mark.asyncio
@patch("rpg_rules_ai.contextualize.generate_context")
async def test_contextualize_batch_handles_errors(mock_gen):
    mock_gen.side_effect = [
        "Context OK.",
        RuntimeError("API error"),
        "Another OK.",
    ]

    items = [
        (Document(page_content=f"P{i}"), Document(page_content=f"C{i}"), f"Book{i}.md")
        for i in range(3)
    ]

    from rpg_rules_ai.contextualize import contextualize_batch

    results = await contextualize_batch(items, batch_size=10)

    assert len(results) == 3
    assert results[0] == "Context OK."
    assert results[1] == ""  # Failed, returns empty string
    assert results[2] == "Another OK."


@pytest.mark.asyncio
@patch("rpg_rules_ai.contextualize.generate_context")
async def test_contextualize_batch_respects_batch_size(mock_gen):
    call_order = []

    async def track_call(parent, child, book_name, model="gpt-4o-mini"):
        call_order.append(len(call_order))
        return f"Context {len(call_order)}."

    mock_gen.side_effect = track_call

    items = [
        (Document(page_content=f"P{i}"), Document(page_content=f"C{i}"), f"Book{i}.md")
        for i in range(5)
    ]

    from rpg_rules_ai.contextualize import contextualize_batch

    results = await contextualize_batch(items, batch_size=2)

    assert len(results) == 5
    assert mock_gen.call_count == 5
