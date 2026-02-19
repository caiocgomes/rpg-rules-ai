"""Layered ingestion pipeline with per-file processing for bounded memory usage.

Each file goes through parse → split → [contextualize] → [entity extract+store] →
embed+store before the next file starts. Embeddings are generated and stored in
batches, never accumulated in memory.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from rpg_rules_ai.chunking import split_into_sections, split_parents_into_children, split_sections_into_parents
from rpg_rules_ai.config import settings
from rpg_rules_ai.retriever import CHROMA_BATCH_LIMIT, get_docstore, get_vectorstore

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 500


class PhaseProgress:
    """Tracks and reports progress by pipeline phase."""

    def __init__(self, callback: Callable | None = None):
        self._callback = callback
        self.phase: str = ""
        self.phase_completed: int = 0
        self.phase_total: int = 0
        self.file_results: list[dict] = []
        self.status: Literal["running", "done", "error"] = "running"
        self.error: str | None = None

    def start_phase(self, phase: str, total: int) -> None:
        self.phase = phase
        self.phase_completed = 0
        self.phase_total = total
        self._notify()

    def advance(self, count: int = 1) -> None:
        self.phase_completed += count
        self._notify()

    def record_file(self, filename: str, status: str, error_message: str | None = None) -> None:
        self.file_results.append({
            "filename": filename,
            "status": status,
            "error_message": error_message,
        })

    def _notify(self) -> None:
        if self._callback:
            self._callback(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "phase": self.phase,
            "phase_completed": self.phase_completed,
            "phase_total": self.phase_total,
            "file_results": list(self.file_results),
            "error": self.error,
        }


def run_layered_pipeline(
    paths: list[Path],
    replace: bool = False,
    on_progress: Callable | None = None,
) -> dict:
    """Execute the ingestion pipeline, processing one file at a time.

    Each file goes through the full pipeline (parse → split → embed → store)
    before the next file starts. This bounds peak memory to a single file's
    worth of data.
    """
    progress = PhaseProgress(callback=on_progress)

    try:
        from rpg_rules_ai.ingest import delete_book, get_indexed_books

        indexed = get_indexed_books()
        progress.start_phase("ingesting", len(paths))

        for path in paths:
            book_name = path.name
            try:
                if book_name in indexed:
                    if replace:
                        delete_book(book_name)
                    else:
                        progress.record_file(book_name, "skipped")
                        progress.advance()
                        continue

                _process_single_file(path, book_name, progress)
                progress.record_file(book_name, "success")
            except Exception as exc:
                logger.error("Failed to ingest '%s': %s", book_name, exc)
                progress.record_file(book_name, "error", str(exc))
            progress.advance()

        progress.status = "done"
        progress._notify()
    except Exception as exc:
        progress.status = "error"
        progress.error = str(exc)
        progress._notify()
        raise

    return progress.to_dict()


def _process_single_file(path: Path, book_name: str, progress: PhaseProgress) -> None:
    """Run the full pipeline for a single file: parse → split → embed+store."""
    # Parse
    docs = _parse_file(path, book_name)

    # Split
    parents, children, parent_map = _split_docs(docs, book_name)

    # Contextualize (optional)
    if settings.enable_contextual_embeddings:
        children = _contextualize_chunks(children, parent_map)

    # Entity extraction + immediate store (optional)
    if settings.enable_entity_extraction:
        _extract_and_store_entities(parents)

    # Embed and store (streaming: embed batch → store batch → discard)
    _embed_and_store(children, parent_map)


def _parse_file(path: Path, book_name: str) -> list[Document]:
    """Parse a single file into Documents."""
    if path.suffix.lower() == ".pdf":
        from rpg_rules_ai.extraction import clean_page_artifacts, extract_pdf, postprocess_headers

        raw_md = extract_pdf(path)
        md = postprocess_headers(clean_page_artifacts(raw_md))
        return [Document(page_content=md, metadata={"book": book_name, "source": str(path)})]

    loader = UnstructuredMarkdownLoader(str(path))
    docs = loader.load()
    for doc in docs:
        doc.metadata["book"] = book_name
    return docs


def _split_docs(
    docs: list[Document], book_name: str
) -> tuple[list[Document], list[Document], dict[str, Document]]:
    """Split documents into parent and child chunks."""
    all_parents: list[Document] = []
    for doc in docs:
        sections = split_into_sections(doc.page_content)
        for section in sections:
            section.metadata["book"] = book_name
        parents = split_sections_into_parents(sections)
        for parent in parents:
            if "book" not in parent.metadata:
                parent.metadata["book"] = book_name
        all_parents.extend(parents)

    children, parent_map = split_parents_into_children(all_parents)
    return all_parents, children, parent_map


def _contextualize_chunks(
    children: list[Document],
    parent_map: dict[str, Document],
) -> list[Document]:
    """Generate context prefixes for child chunks using their parents."""
    from rpg_rules_ai.contextualize import contextualize_batch

    items: list[tuple[Document, Document, str]] = []
    for child in children:
        parent_id = child.metadata.get("doc_id", "")
        parent = parent_map.get(parent_id)
        if parent is None:
            items.append((child, child, child.metadata.get("book", "")))
        else:
            items.append((parent, child, child.metadata.get("book", "")))

    prefixes = asyncio.run(
        contextualize_batch(items, model=settings.context_model)
    )

    enriched: list[Document] = []
    for child, prefix in zip(children, prefixes):
        if prefix:
            new_metadata = {**child.metadata, "original_text": child.page_content, "context_prefix": prefix}
            enriched_content = prefix + "\n\n" + child.page_content
            enriched.append(Document(page_content=enriched_content, metadata=new_metadata))
        else:
            enriched.append(child)

    return enriched


def _extract_and_store_entities(parents: list[Document]) -> None:
    """Extract entities from parent chunks and store immediately."""
    from rpg_rules_ai.entity_extractor import extract_entities_batch
    from rpg_rules_ai.entity_index import EntityIndex

    items: list[tuple[Document, str]] = []
    parent_ids: list[str] = []
    for parent in parents:
        book = parent.metadata.get("book", "")
        doc_id = parent.metadata.get("doc_id", "")
        items.append((parent, book))
        parent_ids.append(doc_id)

    batch_results = asyncio.run(
        extract_entities_batch(items, model=settings.context_model)
    )

    index = EntityIndex()
    try:
        for i, entities in enumerate(batch_results):
            if entities:
                book = items[i][1]
                index.add_entities(book, parent_ids[i], entities)
    finally:
        index.close()


def _embed_and_store(
    children: list[Document],
    parent_map: dict[str, Document],
) -> None:
    """Embed child chunks in batches and store each batch immediately.

    Never holds all embeddings in memory at once.
    """
    embedder = OpenAIEmbeddings(model=settings.embedding_model)
    vs = get_vectorstore()
    collection = vs._collection

    batch_size = min(EMBED_BATCH_SIZE, CHROMA_BATCH_LIMIT)

    for i in range(0, len(children), batch_size):
        batch = children[i : i + batch_size]
        texts = [c.page_content for c in batch]

        batch_embeddings = embedder.embed_documents(texts)

        ids = [str(uuid.uuid4()) for _ in batch]
        documents = [c.page_content for c in batch]
        metadatas = [c.metadata for c in batch]

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=batch_embeddings,
            metadatas=metadatas,
        )

    # Store parents in docstore
    from langchain_core.load import dumps
    docstore = get_docstore()
    docstore.mset([
        (pid, dumps(parent).encode("utf-8"))
        for pid, parent in parent_map.items()
    ])
