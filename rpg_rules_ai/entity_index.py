"""SQLite-backed entity index mapping GURPS entities to books and chunks."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from rpg_rules_ai.config import settings

ENTITY_TYPES = frozenset({
    "advantage", "disadvantage", "skill", "technique",
    "maneuver", "spell", "equipment", "modifier", "other",
})

MENTION_TYPES = frozenset({"defines", "references"})

_ARTICLES = re.compile(r"\b(the|a|an)\b", re.IGNORECASE)

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    normalized TEXT NOT NULL,
    entity_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_mentions (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities(id),
    book TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    mention_type TEXT NOT NULL,
    context TEXT
);

CREATE INDEX IF NOT EXISTS idx_entity_normalized ON entities(normalized);
CREATE INDEX IF NOT EXISTS idx_mention_entity ON entity_mentions(entity_id);
CREATE INDEX IF NOT EXISTS idx_mention_book ON entity_mentions(book);
CREATE INDEX IF NOT EXISTS idx_mention_chunk ON entity_mentions(chunk_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_unique ON entities(normalized, entity_type);
"""


def normalize_entity_name(name: str) -> str:
    """Lowercase, strip articles, collapse whitespace, replace spaces with underscores."""
    s = name.lower().strip()
    s = _ARTICLES.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.replace(" ", "_")


@dataclass
class EntityMention:
    entity_name: str
    entity_type: str
    book: str
    chunk_id: str
    mention_type: str
    context: str | None = None


class EntityIndex:
    """SQLite-backed index of GURPS entities and their locations in the corpus."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_path = settings.entity_index_path
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA_SQL)

    def close(self) -> None:
        self._conn.close()

    def _get_or_create_entity(self, name: str, entity_type: str) -> int:
        normalized = normalize_entity_name(name)
        row = self._conn.execute(
            "SELECT id FROM entities WHERE normalized = ? AND entity_type = ?",
            (normalized, entity_type),
        ).fetchone()
        if row:
            return row[0]
        cursor = self._conn.execute(
            "INSERT INTO entities (name, normalized, entity_type) VALUES (?, ?, ?)",
            (name, normalized, entity_type),
        )
        return cursor.lastrowid

    def add_entities(
        self,
        book: str,
        chunk_id: str,
        entities: list[dict],
    ) -> None:
        """Insert extracted entities for a chunk.

        Each entity dict must have keys: name, type, mention_type.
        Optional key: context.
        """
        for ent in entities:
            etype = ent["type"] if ent["type"] in ENTITY_TYPES else "other"
            mtype = ent["mention_type"] if ent["mention_type"] in MENTION_TYPES else "references"
            entity_id = self._get_or_create_entity(ent["name"], etype)
            self._conn.execute(
                "INSERT INTO entity_mentions (entity_id, book, chunk_id, mention_type, context) "
                "VALUES (?, ?, ?, ?, ?)",
                (entity_id, book, chunk_id, mtype, ent.get("context")),
            )
        self._conn.commit()

    def query_entity(self, name: str) -> list[EntityMention]:
        """Find all mentions of an entity (fuzzy by normalized name)."""
        normalized = normalize_entity_name(name)
        rows = self._conn.execute(
            """
            SELECT e.name, e.entity_type, m.book, m.chunk_id, m.mention_type, m.context
            FROM entity_mentions m
            JOIN entities e ON e.id = m.entity_id
            WHERE e.normalized = ?
            """,
            (normalized,),
        ).fetchall()
        return [
            EntityMention(
                entity_name=r[0], entity_type=r[1], book=r[2],
                chunk_id=r[3], mention_type=r[4], context=r[5],
            )
            for r in rows
        ]

    def query_cross_book(
        self,
        entity_names: list[str],
        exclude_book: str,
    ) -> list[EntityMention]:
        """Find mentions of entities in books other than exclude_book."""
        if not entity_names:
            return []
        normalized = [normalize_entity_name(n) for n in entity_names]
        placeholders = ",".join("?" for _ in normalized)
        rows = self._conn.execute(
            f"""
            SELECT e.name, e.entity_type, m.book, m.chunk_id, m.mention_type, m.context
            FROM entity_mentions m
            JOIN entities e ON e.id = m.entity_id
            WHERE e.normalized IN ({placeholders})
              AND m.book != ?
            """,
            (*normalized, exclude_book),
        ).fetchall()
        return [
            EntityMention(
                entity_name=r[0], entity_type=r[1], book=r[2],
                chunk_id=r[3], mention_type=r[4], context=r[5],
            )
            for r in rows
        ]

    def query_entity_by_chunk(self, chunk_id: str) -> list[EntityMention]:
        """Find all entities mentioned in a specific chunk."""
        rows = self._conn.execute(
            """
            SELECT e.name, e.entity_type, m.book, m.chunk_id, m.mention_type, m.context
            FROM entity_mentions m
            JOIN entities e ON e.id = m.entity_id
            WHERE m.chunk_id = ?
            """,
            (chunk_id,),
        ).fetchall()
        return [
            EntityMention(
                entity_name=r[0], entity_type=r[1], book=r[2],
                chunk_id=r[3], mention_type=r[4], context=r[5],
            )
            for r in rows
        ]

    def delete_book_entities(self, book: str) -> None:
        """Remove all mentions for a book and garbage-collect orphan entities."""
        self._conn.execute(
            "DELETE FROM entity_mentions WHERE book = ?", (book,)
        )
        self._conn.execute(
            "DELETE FROM entities WHERE id NOT IN (SELECT DISTINCT entity_id FROM entity_mentions)"
        )
        self._conn.commit()

    def get_book_entity_count(self, book: str) -> int:
        """Count distinct entities mentioned in a book."""
        row = self._conn.execute(
            "SELECT COUNT(DISTINCT entity_id) FROM entity_mentions WHERE book = ?",
            (book,),
        ).fetchone()
        return row[0]

    def build_graph_for_chunks(self, chunk_ids: list[str]) -> dict:
        """Build a graph of entities, books, and their relationships for given chunks.

        Returns {nodes: [...], edges: [...]} suitable for vis.js rendering.
        """
        if not chunk_ids:
            return {"nodes": [], "edges": []}

        # 1. Get all entities in the given chunks
        placeholders = ",".join("?" for _ in chunk_ids)
        rows = self._conn.execute(
            f"""
            SELECT DISTINCT e.id, e.name, e.entity_type, m.book, m.chunk_id, m.mention_type
            FROM entity_mentions m
            JOIN entities e ON e.id = m.entity_id
            WHERE m.chunk_id IN ({placeholders})
            """,
            chunk_ids,
        ).fetchall()

        if not rows:
            return {"nodes": [], "edges": []}

        # Collect entity ids and books from the direct chunks
        entity_ids = {r[0] for r in rows}
        direct_books = {r[3] for r in rows}

        # 2. Get cross-book mentions for those entities (1-hop expansion)
        eid_placeholders = ",".join("?" for _ in entity_ids)
        cross_rows = self._conn.execute(
            f"""
            SELECT DISTINCT e.id, e.name, e.entity_type, m.book, m.mention_type
            FROM entity_mentions m
            JOIN entities e ON e.id = m.entity_id
            WHERE e.id IN ({eid_placeholders})
              AND m.chunk_id NOT IN ({placeholders})
            """,
            [*entity_ids, *chunk_ids],
        ).fetchall()

        # 3. Build nodes and edges
        nodes = []
        edges = []
        seen_nodes = set()
        seen_edges = set()

        # Entity nodes
        all_entity_rows = list(rows) + [(r[0], r[1], r[2], r[3], None, r[4]) for r in cross_rows]
        for r in all_entity_rows:
            eid, name, etype = r[0], r[1], r[2]
            node_id = f"entity_{eid}"
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                is_direct = eid in entity_ids
                nodes.append({
                    "id": node_id,
                    "label": name,
                    "type": "entity",
                    "entity_type": etype,
                    "direct": is_direct,
                })

        # Book nodes
        all_books = direct_books | {r[3] for r in cross_rows}
        for book in all_books:
            node_id = f"book_{book}"
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                nodes.append({
                    "id": node_id,
                    "label": book.replace(".md", ""),
                    "type": "book",
                    "direct": book in direct_books,
                })

        # Edges: entity -> book (from direct chunks)
        for r in rows:
            eid, book, mention_type = r[0], r[3], r[5]
            edge_key = (f"entity_{eid}", f"book_{book}")
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append({
                    "from": edge_key[0],
                    "to": edge_key[1],
                    "relation": mention_type,
                    "direct": True,
                })

        # Edges: entity -> book (from cross-book mentions)
        for r in cross_rows:
            eid, book, mention_type = r[0], r[3], r[4]
            edge_key = (f"entity_{eid}", f"book_{book}")
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append({
                    "from": edge_key[0],
                    "to": edge_key[1],
                    "relation": mention_type,
                    "direct": False,
                })

        return {"nodes": nodes, "edges": edges}

    def get_entity_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM entities").fetchone()
        return row[0]

    def get_mention_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()
        return row[0]
