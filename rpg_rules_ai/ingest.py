from __future__ import annotations

import logging
from pathlib import Path

from rpg_rules_ai.config import settings
from rpg_rules_ai.retriever import get_docstore, get_vectorstore

logger = logging.getLogger(__name__)


def delete_book(book_name: str) -> None:
    """Remove all chunks for a book from vectorstore and docstore.

    Idempotent: no error if the book doesn't exist.
    Does NOT delete the source file from SOURCES_DIR.
    """
    vs = get_vectorstore()
    collection = vs._collection

    # Collect parent doc_ids from children before deleting
    result = collection.get(where={"book": book_name}, include=["metadatas"])
    parent_ids = {
        m.get("doc_id")
        for m in result["metadatas"]
        if m.get("doc_id")
    }

    collection.delete(where={"book": book_name})

    if parent_ids:
        docstore = get_docstore()
        for pid in parent_ids:
            docstore.mdelete([pid])

    # Clean entity index
    try:
        from rpg_rules_ai.entity_index import EntityIndex
        entity_idx = EntityIndex()
        try:
            entity_idx.delete_book_entities(book_name)
        finally:
            entity_idx.close()
    except Exception as exc:
        logger.warning("Failed to clean entity index for '%s': %s", book_name, exc)

    logger.info("Deleted book '%s' from index (%d parent chunks).", book_name, len(parent_ids))


def _get_all_metadatas() -> list[dict]:
    """Fetch all metadatas from Chroma in batches to avoid SQLite variable limit."""
    vs = get_vectorstore()
    collection = vs._collection
    total = collection.count()
    if total == 0:
        return []

    all_metadatas: list[dict] = []
    batch_size = 1000
    offset = 0
    while offset < total:
        batch = collection.get(
            include=["metadatas"],
            limit=batch_size,
            offset=offset,
        )
        all_metadatas.extend(batch["metadatas"])
        offset += batch_size
    return all_metadatas


def get_books_metadata() -> list[dict]:
    """Return metadata for each indexed book.

    Each entry has: book, chunk_count, parent_count, entity_count, has_source.
    """
    chunk_counts: dict[str, int] = {}
    parent_ids_per_book: dict[str, set] = {}
    for m in _get_all_metadatas():
        book = m.get("book")
        if book:
            chunk_counts[book] = chunk_counts.get(book, 0) + 1
            doc_id = m.get("doc_id")
            if doc_id:
                parent_ids_per_book.setdefault(book, set()).add(doc_id)

    # Entity counts (best-effort, don't break if index unavailable)
    entity_counts: dict[str, int] = {}
    try:
        from rpg_rules_ai.entity_index import EntityIndex
        idx = EntityIndex()
        try:
            for book in chunk_counts:
                entity_counts[book] = idx.get_book_entity_count(book)
        finally:
            idx.close()
    except Exception as exc:
        logger.debug("Entity index unavailable for metadata: %s", exc)

    sources_path = Path(settings.sources_dir)
    return [
        {
            "book": book,
            "chunk_count": count,
            "parent_count": len(parent_ids_per_book.get(book, set())),
            "entity_count": entity_counts.get(book, 0),
            "has_source": (sources_path / book).exists(),
        }
        for book, count in sorted(chunk_counts.items())
    ]


def get_indexed_books() -> list[str]:
    """Return distinct book names currently in the Chroma collection."""
    books = {m.get("book") for m in _get_all_metadatas() if m.get("book")}
    return sorted(books)


def reindex_directory(directory: str | Path) -> int:
    """Clear the collection and re-ingest all .md files from directory.

    Returns total number of documents ingested via the layered pipeline.
    """
    from rpg_rules_ai.pipeline import run_layered_pipeline

    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")
    md_files = sorted(directory.glob("*.md"))

    vs = get_vectorstore()
    vs.reset_collection()

    result = run_layered_pipeline(md_files, replace=False)
    success_count = sum(1 for r in result.get("file_results", []) if r["status"] == "success")
    return success_count
