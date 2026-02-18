"""Tests for SQLite entity index CRUD, cross-book queries, and delete consistency."""

import pytest

from caprag.entity_index import EntityIndex, normalize_entity_name


@pytest.fixture
def index(tmp_path):
    db = tmp_path / "test_entities.db"
    idx = EntityIndex(db_path=db)
    yield idx
    idx.close()


def _ent(name, etype="advantage", mention="defines", context=None):
    return {"name": name, "type": etype, "mention_type": mention, "context": context}


class TestNormalization:
    def test_basic(self):
        assert normalize_entity_name("Rapid Strike") == "rapid_strike"

    def test_strips_articles(self):
        assert normalize_entity_name("The Enhanced Time Sense") == "enhanced_time_sense"

    def test_collapses_whitespace(self):
        assert normalize_entity_name("  combat   reflexes  ") == "combat_reflexes"


class TestAddAndQuery:
    def test_add_and_query_single_entity(self, index):
        index.add_entities("Basic Set", "chunk1", [_ent("Rapid Strike", "maneuver")])
        results = index.query_entity("Rapid Strike")
        assert len(results) == 1
        assert results[0].entity_name == "Rapid Strike"
        assert results[0].book == "Basic Set"
        assert results[0].mention_type == "defines"

    def test_query_is_case_insensitive(self, index):
        index.add_entities("Basic Set", "chunk1", [_ent("Magery", "advantage")])
        results = index.query_entity("magery")
        assert len(results) == 1

    def test_query_ignores_articles(self, index):
        index.add_entities("Basic Set", "chunk1", [_ent("The Enhanced Time Sense")])
        results = index.query_entity("Enhanced Time Sense")
        assert len(results) == 1

    def test_multiple_mentions_same_entity(self, index):
        index.add_entities("Basic Set", "chunk1", [_ent("Rapid Strike", "maneuver", "defines")])
        index.add_entities("Martial Arts", "chunk2", [_ent("Rapid Strike", "maneuver", "references")])
        results = index.query_entity("Rapid Strike")
        assert len(results) == 2
        books = {r.book for r in results}
        assert books == {"Basic Set", "Martial Arts"}

    def test_multiple_entities_per_chunk(self, index):
        entities = [
            _ent("Magery", "advantage"),
            _ent("Fireball", "spell"),
            _ent("Staff", "equipment"),
        ]
        index.add_entities("Magic", "chunk1", entities)
        assert index.get_entity_count() == 3
        assert index.get_mention_count() == 3

    def test_invalid_type_falls_back_to_other(self, index):
        index.add_entities("Book", "c1", [_ent("Weird Thing", "nonexistent_type")])
        results = index.query_entity("Weird Thing")
        assert results[0].entity_type == "other"

    def test_invalid_mention_type_falls_back_to_references(self, index):
        index.add_entities("Book", "c1", [{"name": "X", "type": "skill", "mention_type": "bogus"}])
        results = index.query_entity("X")
        assert results[0].mention_type == "references"


class TestCrossBook:
    def test_cross_book_excludes_source(self, index):
        index.add_entities("Basic Set", "c1", [_ent("Rapid Strike", "maneuver", "defines")])
        index.add_entities("Martial Arts", "c2", [_ent("Rapid Strike", "maneuver", "references")])
        results = index.query_cross_book(["Rapid Strike"], exclude_book="Basic Set")
        assert len(results) == 1
        assert results[0].book == "Martial Arts"

    def test_cross_book_multiple_entities(self, index):
        index.add_entities("Basic Set", "c1", [_ent("Magery"), _ent("Fireball", "spell")])
        index.add_entities("Magic", "c2", [_ent("Magery", mention="references"), _ent("Fireball", "spell", "defines")])
        results = index.query_cross_book(["Magery", "Fireball"], exclude_book="Basic Set")
        assert len(results) == 2
        assert all(r.book == "Magic" for r in results)

    def test_cross_book_empty_names(self, index):
        assert index.query_cross_book([], exclude_book="Basic Set") == []

    def test_cross_book_no_matches(self, index):
        index.add_entities("Basic Set", "c1", [_ent("Magery")])
        results = index.query_cross_book(["Magery"], exclude_book="Basic Set")
        assert results == []


class TestDelete:
    def test_delete_removes_mentions(self, index):
        index.add_entities("Basic Set", "c1", [_ent("Magery")])
        index.add_entities("Magic", "c2", [_ent("Magery", mention="references")])
        index.delete_book_entities("Basic Set")
        results = index.query_entity("Magery")
        assert len(results) == 1
        assert results[0].book == "Magic"

    def test_delete_garbage_collects_orphans(self, index):
        index.add_entities("Basic Set", "c1", [_ent("Unique Advantage")])
        assert index.get_entity_count() == 1
        index.delete_book_entities("Basic Set")
        assert index.get_entity_count() == 0

    def test_delete_preserves_shared_entities(self, index):
        index.add_entities("Basic Set", "c1", [_ent("Magery")])
        index.add_entities("Magic", "c2", [_ent("Magery", mention="references")])
        index.delete_book_entities("Basic Set")
        assert index.get_entity_count() == 1

    def test_delete_nonexistent_book_is_safe(self, index):
        index.delete_book_entities("NonexistentBook")
        assert index.get_entity_count() == 0

    def test_delete_then_readd(self, index):
        index.add_entities("Book", "c1", [_ent("Magery")])
        index.delete_book_entities("Book")
        index.add_entities("Book", "c1", [_ent("Magery")])
        assert index.get_entity_count() == 1
        assert index.get_mention_count() == 1


class TestBuildGraphForChunks:
    def test_returns_empty_for_no_chunks(self, index):
        result = index.build_graph_for_chunks([])
        assert result == {"nodes": [], "edges": []}

    def test_returns_empty_for_unknown_chunks(self, index):
        result = index.build_graph_for_chunks(["nonexistent"])
        assert result == {"nodes": [], "edges": []}

    def test_builds_graph_with_direct_entities(self, index):
        index.add_entities("Basic Set", "c1", [
            _ent("Rapid Strike", etype="maneuver", mention="defines"),
            _ent("DX", etype="other", mention="references"),
        ])
        result = index.build_graph_for_chunks(["c1"])
        nodes = {n["label"]: n for n in result["nodes"]}
        assert "Rapid Strike" in nodes
        assert "DX" in nodes
        assert "Basic Set" in nodes
        assert nodes["Rapid Strike"]["type"] == "entity"
        assert nodes["Rapid Strike"]["direct"] is True
        assert nodes["Basic Set"]["type"] == "book"
        assert len(result["edges"]) == 2

    def test_includes_cross_book_mentions(self, index):
        index.add_entities("Basic Set", "c1", [
            _ent("Rapid Strike", etype="maneuver", mention="defines"),
        ])
        index.add_entities("Martial Arts", "c2", [
            _ent("Rapid Strike", etype="maneuver", mention="references"),
        ])
        result = index.build_graph_for_chunks(["c1"])
        nodes = {n["label"]: n for n in result["nodes"]}
        assert "Martial Arts" in nodes
        assert nodes["Martial Arts"]["direct"] is False
        # Should have edges: Rapid Strike -> Basic Set (direct), Rapid Strike -> Martial Arts (cross)
        direct_edges = [e for e in result["edges"] if e["direct"]]
        cross_edges = [e for e in result["edges"] if not e["direct"]]
        assert len(direct_edges) == 1
        assert len(cross_edges) == 1

    def test_no_duplicate_nodes_or_edges(self, index):
        index.add_entities("Book", "c1", [_ent("Magery")])
        index.add_entities("Book", "c2", [_ent("Magery")])
        result = index.build_graph_for_chunks(["c1", "c2"])
        entity_nodes = [n for n in result["nodes"] if n["type"] == "entity"]
        assert len(entity_nodes) == 1
