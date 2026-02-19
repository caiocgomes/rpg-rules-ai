"""Tests for entity extraction via mocked LLM."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from rpg_rules_ai.entity_extractor import ExtractedEntities, ExtractedEntity


@pytest.fixture
def parent_doc():
    return Document(
        page_content="Rapid Strike (p. B370) lets you attack twice at -6 per attack.",
        metadata={"book": "Martial Arts", "doc_id": "chunk1"},
    )


@pytest.mark.asyncio
@patch("rpg_rules_ai.entity_extractor.ChatOpenAI")
@patch("rpg_rules_ai.entity_extractor.ChatPromptTemplate")
async def test_extract_entities_returns_list(mock_prompt_cls, mock_chat_cls, parent_doc):
    mock_result = ExtractedEntities(entities=[
        ExtractedEntity(name="Rapid Strike", type="maneuver", mention_type="defines"),
    ])

    mock_chain = AsyncMock()
    mock_chain.ainvoke = AsyncMock(return_value=mock_result)

    mock_prompt = MagicMock()
    mock_prompt.__or__ = MagicMock(return_value=mock_chain)
    mock_prompt_cls.from_template.return_value = mock_prompt

    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=MagicMock())
    mock_chat_cls.return_value = mock_llm

    from rpg_rules_ai.entity_extractor import extract_entities

    result = await extract_entities(parent_doc, "Martial Arts")

    assert len(result) == 1
    assert result[0]["name"] == "Rapid Strike"
    assert result[0]["type"] == "maneuver"
    assert result[0]["mention_type"] == "defines"


@pytest.mark.asyncio
@patch("rpg_rules_ai.entity_extractor.extract_entities")
async def test_batch_processes_all(mock_extract):
    mock_extract.side_effect = [
        [{"name": "Magery", "type": "advantage", "mention_type": "defines"}],
        [{"name": "Fireball", "type": "spell", "mention_type": "references"}],
    ]

    items = [
        (Document(page_content=f"P{i}"), f"Book{i}.md")
        for i in range(2)
    ]

    from rpg_rules_ai.entity_extractor import extract_entities_batch

    results = await extract_entities_batch(items, batch_size=10)

    assert len(results) == 2
    assert results[0][0]["name"] == "Magery"
    assert results[1][0]["name"] == "Fireball"


@pytest.mark.asyncio
@patch("rpg_rules_ai.entity_extractor.extract_entities")
async def test_batch_handles_errors(mock_extract):
    mock_extract.side_effect = [
        [{"name": "Magery", "type": "advantage", "mention_type": "defines"}],
        RuntimeError("API error"),
        [{"name": "Staff", "type": "equipment", "mention_type": "references"}],
    ]

    items = [
        (Document(page_content=f"P{i}"), f"Book{i}.md")
        for i in range(3)
    ]

    from rpg_rules_ai.entity_extractor import extract_entities_batch

    results = await extract_entities_batch(items, batch_size=10)

    assert len(results) == 3
    assert results[0][0]["name"] == "Magery"
    assert results[1] == []
    assert results[2][0]["name"] == "Staff"


@pytest.mark.asyncio
@patch("rpg_rules_ai.entity_extractor.extract_entities")
async def test_batch_empty_input(mock_extract):
    from rpg_rules_ai.entity_extractor import extract_entities_batch

    results = await extract_entities_batch([], batch_size=10)
    assert results == []
    mock_extract.assert_not_called()
