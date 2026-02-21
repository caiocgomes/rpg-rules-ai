"""Tests for multi-hop cross-book retrieval via entity index."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from rpg_rules_ai.entity_index import EntityIndex, EntityMention
from rpg_rules_ai.schemas import Question, Questions, State
from rpg_rules_ai.strategies.multi_hop import MultiHopStrategy, SufficiencyAnalysis


def _make_doc(content: str, book: str = "Basic Set", doc_id: str = "") -> Document:
    meta = {"book": book}
    if doc_id:
        meta["doc_id"] = doc_id
    return Document(page_content=content, metadata=meta)


def _make_state(question: str) -> dict:
    msg = MagicMock()
    msg.content = question
    return {"messages": [msg], "main_question": question}


class TestEntityCrossBookQueries:
    def test_returns_empty_when_entity_extraction_disabled(self):
        strategy = MultiHopStrategy()
        docs = [_make_doc("Rapid Strike", "Basic Set", "c1")]
        with patch("rpg_rules_ai.strategies.multi_hop.settings") as mock_settings:
            mock_settings.enable_entity_retrieval = False
            result = strategy._entity_cross_book_queries(docs)
        assert result == []

    def test_returns_queries_for_cross_book_entities(self, tmp_path):
        db_path = tmp_path / "test.db"
        index = EntityIndex(db_path=db_path)
        index.add_entities("Basic Set", "c1", [
            {"name": "Rapid Strike", "type": "maneuver", "mention_type": "defines"},
        ])
        index.add_entities("Martial Arts", "c2", [
            {"name": "Rapid Strike", "type": "maneuver", "mention_type": "references"},
        ])

        strategy = MultiHopStrategy()
        docs = [_make_doc("Rapid Strike info", "Basic Set", "c1")]

        with (
            patch("rpg_rules_ai.strategies.multi_hop.settings") as mock_settings,
            patch("rpg_rules_ai.entity_index.settings") as mock_ei_settings,
        ):
            mock_settings.enable_entity_retrieval = True
            mock_ei_settings.entity_index_path = str(db_path)
            result = strategy._entity_cross_book_queries(docs)

        assert len(result) == 1
        assert "Rapid Strike" in result[0].question
        assert "Martial Arts" in result[0].question
        index.close()

    def test_no_cross_book_when_all_in_context(self, tmp_path):
        db_path = tmp_path / "test.db"
        index = EntityIndex(db_path=db_path)
        index.add_entities("Basic Set", "c1", [
            {"name": "Magery", "type": "advantage", "mention_type": "defines"},
        ])

        strategy = MultiHopStrategy()
        docs = [_make_doc("Magery info", "Basic Set", "c1")]

        with (
            patch("rpg_rules_ai.strategies.multi_hop.settings") as mock_settings,
            patch("rpg_rules_ai.entity_index.settings") as mock_ei_settings,
        ):
            mock_settings.enable_entity_retrieval = True
            mock_ei_settings.entity_index_path = str(db_path)
            result = strategy._entity_cross_book_queries(docs)

        assert result == []
        index.close()

    def test_handles_entity_index_errors_gracefully(self, tmp_path):
        strategy = MultiHopStrategy()
        docs = [_make_doc("Content", "Book", "c1")]

        with (
            patch("rpg_rules_ai.strategies.multi_hop.settings") as mock_settings,
            patch("rpg_rules_ai.entity_index.settings") as mock_ei_settings,
        ):
            mock_settings.enable_entity_retrieval = True
            mock_ei_settings.entity_index_path = "/nonexistent/path/db.sqlite"
            result = strategy._entity_cross_book_queries(docs)

        # Should handle gracefully (either empty or exception caught)
        assert isinstance(result, list)


class TestQueryEntityByChunk:
    def test_finds_entities_for_chunk(self, tmp_path):
        db_path = tmp_path / "test.db"
        index = EntityIndex(db_path=db_path)
        index.add_entities("Basic Set", "chunk_abc", [
            {"name": "Magery", "type": "advantage", "mention_type": "defines"},
            {"name": "Fireball", "type": "spell", "mention_type": "references"},
        ])

        results = index.query_entity_by_chunk("chunk_abc")
        assert len(results) == 2
        names = {r.entity_name for r in results}
        assert names == {"Magery", "Fireball"}
        index.close()

    def test_returns_empty_for_unknown_chunk(self, tmp_path):
        db_path = tmp_path / "test.db"
        index = EntityIndex(db_path=db_path)
        results = index.query_entity_by_chunk("nonexistent")
        assert results == []
        index.close()
