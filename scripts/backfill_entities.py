"""Backfill entity index from existing parent chunks in docstore.

Reads all parent documents, extracts entities via LLM, and populates
the entity index. Does NOT re-embed or re-ingest.

Usage:
    uv run python scripts/backfill_entities.py [--books BOOK1 BOOK2] [--dry-run] [--limit N]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.load import loads

from caprag.config import settings
from caprag.entity_extractor import extract_entities_batch
from caprag.entity_index import EntityIndex
from caprag.retriever import get_docstore, get_vectorstore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def get_parent_docs_for_book(book_name: str) -> list[tuple[str, any]]:
    """Get all parent documents for a book from vectorstore + docstore."""
    vs = get_vectorstore()
    collection = vs._collection
    docstore = get_docstore()

    # Get all child chunks for this book and collect unique parent doc_ids
    all_doc_ids = set()
    batch_size = 1000
    offset = 0
    while True:
        result = collection.get(
            where={"book": book_name},
            include=["metadatas"],
            limit=batch_size,
            offset=offset,
        )
        if not result["metadatas"]:
            break
        for meta in result["metadatas"]:
            doc_id = meta.get("doc_id", "")
            if doc_id:
                all_doc_ids.add(doc_id)
        offset += batch_size

    # Load parent docs from docstore
    parents = []
    for doc_id in all_doc_ids:
        data = docstore.mget([doc_id])
        if data and data[0] is not None:
            doc = loads(data[0].decode("utf-8"))
            parents.append((doc_id, doc))

    return parents


async def backfill_book(
    book_name: str,
    index: EntityIndex,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    """Extract entities from all parent chunks of a book and insert into index."""
    logger.info("Loading parents for '%s'...", book_name)
    parents = get_parent_docs_for_book(book_name)
    logger.info("Found %d parent chunks for '%s'", len(parents), book_name)

    if limit:
        parents = parents[:limit]
        logger.info("Limited to %d parents", limit)

    items = [(doc, book_name) for _, doc in parents]
    doc_ids = [doc_id for doc_id, _ in parents]

    logger.info("Extracting entities from %d parents...", len(items))
    start = time.time()
    results = await extract_entities_batch(
        items, model=settings.entity_extraction_model, batch_size=20
    )
    elapsed = time.time() - start
    logger.info("Extraction took %.1fs", elapsed)

    total_entities = 0
    for i, entities in enumerate(results):
        total_entities += len(entities)
        if not dry_run and entities:
            index.add_entities(book_name, doc_ids[i], entities)

    return {
        "book": book_name,
        "parents": len(parents),
        "entities_extracted": total_entities,
        "elapsed": elapsed,
    }


async def main():
    parser = argparse.ArgumentParser(description="Backfill entity index")
    parser.add_argument("--books", nargs="*", help="Specific books to process")
    parser.add_argument("--dry-run", action="store_true", help="Extract but don't store")
    parser.add_argument("--limit", type=int, help="Limit parents per book")
    args = parser.parse_args()

    from caprag.ingest import get_indexed_books

    if args.books:
        books = args.books
    else:
        books = get_indexed_books()

    logger.info("Will process %d books: %s", len(books), books)

    index = EntityIndex()
    try:
        for book in books:
            # Clear existing entities for this book first
            if not args.dry_run:
                index.delete_book_entities(book)
            stats = await backfill_book(book, index, dry_run=args.dry_run, limit=args.limit)
            logger.info(
                "Book '%s': %d parents, %d entities in %.1fs",
                stats["book"], stats["parents"], stats["entities_extracted"], stats["elapsed"],
            )

        logger.info(
            "Entity index: %d entities, %d mentions",
            index.get_entity_count(),
            index.get_mention_count(),
        )
    finally:
        index.close()


if __name__ == "__main__":
    asyncio.run(main())
