"""Layered ingestion pipeline: parse → split → [contextualize] → embed → store."""

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

from caprag.chunking import split_into_sections, split_parents_into_children, split_sections_into_parents
from caprag.config import settings
from caprag.retriever import CHROMA_BATCH_LIMIT, get_docstore, get_vectorstore

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
    """Execute the full layered ingestion pipeline.

    Returns the final progress dict.
    """
    progress = PhaseProgress(callback=on_progress)

    try:
        # Phase 1: Parse
        all_docs, book_names = _phase_parse(paths, replace, progress)
        if not all_docs:
            progress.status = "done"
            progress._notify()
            return progress.to_dict()

        # Phase 2: Split
        parent_chunks, child_chunks, parent_map = _phase_split(all_docs, progress)

        # Phase 2.5: Contextualize (optional)
        if settings.enable_contextual_embeddings:
            child_chunks = _phase_contextualize(child_chunks, parent_map, progress)

        # Phase 2.6: Entity extraction (optional)
        entity_results = None
        if settings.enable_entity_extraction:
            entity_results = _phase_extract_entities(parent_chunks, all_docs, progress)

        # Phase 3: Embed
        embeddings = _phase_embed(child_chunks, progress)

        # Phase 4: Store
        _phase_store(child_chunks, embeddings, parent_map, progress)

        # Phase 4.5: Store entities (if extracted)
        if entity_results is not None:
            _phase_store_entities(entity_results, progress)

        progress.status = "done"
        progress._notify()
    except Exception as exc:
        progress.status = "error"
        progress.error = str(exc)
        progress._notify()
        raise

    return progress.to_dict()


def _phase_parse(
    paths: list[Path],
    replace: bool,
    progress: PhaseProgress,
) -> tuple[list[Document], list[str]]:
    """Phase 1: Parse markdown and PDF files.

    PDF files are extracted via pymupdf4llm and post-processed to detect headers.
    Markdown files continue through UnstructuredMarkdownLoader.
    """
    from caprag.ingest import delete_book, get_indexed_books

    progress.start_phase("parsing", len(paths))
    indexed = get_indexed_books()
    all_docs: list[Document] = []
    book_names: list[str] = []

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

            if path.suffix.lower() == ".pdf":
                from caprag.extraction import clean_page_artifacts, extract_pdf, postprocess_headers

                raw_md = extract_pdf(path)
                md = postprocess_headers(clean_page_artifacts(raw_md))
                docs = [Document(page_content=md, metadata={"book": book_name, "source": str(path)})]
            else:
                loader = UnstructuredMarkdownLoader(str(path))
                docs = loader.load()
                for doc in docs:
                    doc.metadata["book"] = book_name

            all_docs.extend(docs)
            book_names.append(book_name)
            progress.record_file(book_name, "success")
        except Exception as exc:
            logger.error("Failed to parse '%s': %s", book_name, exc)
            progress.record_file(book_name, "error", str(exc))
        progress.advance()

    return all_docs, book_names


def _phase_split(
    docs: list[Document],
    progress: PhaseProgress,
) -> tuple[list[Document], list[Document], dict[str, Document]]:
    """Phase 2: Section-aware splitting into parent and child chunks.

    For each document: split markdown into sections by headers, then split
    large sections into parent chunks, then split parents into child chunks
    with doc_id linkage.
    """
    progress.start_phase("splitting", len(docs))

    all_parents: list[Document] = []
    for doc in docs:
        book_name = doc.metadata.get("book", "")
        sections = split_into_sections(doc.page_content)
        for section in sections:
            section.metadata["book"] = book_name
        parents = split_sections_into_parents(sections)
        for parent in parents:
            if "book" not in parent.metadata:
                parent.metadata["book"] = book_name
        all_parents.extend(parents)
        progress.advance()

    child_chunks, parent_map = split_parents_into_children(all_parents)
    return all_parents, child_chunks, parent_map


def _phase_contextualize(
    child_chunks: list[Document],
    parent_map: dict[str, Document],
    progress: PhaseProgress,
) -> list[Document]:
    """Phase 2.5: Generate context prefixes for child chunks using their parents."""
    from caprag.contextualize import contextualize_batch

    progress.start_phase("contextualizing", len(child_chunks))

    items: list[tuple[Document, Document, str]] = []
    for child in child_chunks:
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
    for child, prefix in zip(child_chunks, prefixes):
        if prefix:
            new_metadata = {**child.metadata, "original_text": child.page_content, "context_prefix": prefix}
            enriched_content = prefix + "\n\n" + child.page_content
            enriched.append(Document(page_content=enriched_content, metadata=new_metadata))
        else:
            enriched.append(child)
        progress.advance()

    return enriched


def _phase_embed(
    child_chunks: list[Document],
    progress: PhaseProgress,
) -> list[list[float]]:
    """Phase 3: Generate embeddings for all child chunks in batches."""
    embedder = OpenAIEmbeddings(model=settings.embedding_model)
    texts = [c.page_content for c in child_chunks]

    progress.start_phase("embedding", len(texts))
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i : i + EMBED_BATCH_SIZE]
        batch_embeddings = embedder.embed_documents(batch)
        all_embeddings.extend(batch_embeddings)
        progress.advance(len(batch))

    return all_embeddings


def _phase_store(
    child_chunks: list[Document],
    embeddings: list[list[float]],
    parent_map: dict[str, Document],
    progress: PhaseProgress,
) -> None:
    """Phase 4: Store embeddings in Chroma and parents in docstore."""
    vs = get_vectorstore()
    collection = vs._collection
    docstore = get_docstore()

    progress.start_phase("storing", len(child_chunks))

    # Store children with pre-computed embeddings
    for i in range(0, len(child_chunks), CHROMA_BATCH_LIMIT):
        batch_chunks = child_chunks[i : i + CHROMA_BATCH_LIMIT]
        batch_embeddings = embeddings[i : i + CHROMA_BATCH_LIMIT]

        ids = [str(uuid.uuid4()) for _ in batch_chunks]
        documents = [c.page_content for c in batch_chunks]
        metadatas = [c.metadata for c in batch_chunks]

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=batch_embeddings,
            metadatas=metadatas,
        )
        progress.advance(len(batch_chunks))

    # Store parents in docstore (serialized as Document via langchain dumps)
    from langchain_core.load import dumps
    docstore.mset([
        (pid, dumps(parent).encode("utf-8"))
        for pid, parent in parent_map.items()
    ])


def _phase_extract_entities(
    parent_chunks: list[Document],
    all_docs: list[Document],
    progress: PhaseProgress,
) -> list[tuple[str, str, list[dict]]]:
    """Phase 2.6: Extract entities from parent chunks via LLM.

    Returns list of (book_name, parent_doc_id, entities) tuples.
    """
    from caprag.entity_extractor import extract_entities_batch

    items: list[tuple[Document, str]] = []
    parent_ids: list[str] = []
    for parent in parent_chunks:
        book = parent.metadata.get("book", "")
        doc_id = parent.metadata.get("doc_id", "")
        items.append((parent, book))
        parent_ids.append(doc_id)

    progress.start_phase("extracting_entities", len(items))

    batch_results = asyncio.run(
        extract_entities_batch(items, model=settings.context_model)
    )

    results: list[tuple[str, str, list[dict]]] = []
    for i, entities in enumerate(batch_results):
        book = items[i][1]
        pid = parent_ids[i]
        results.append((book, pid, entities))
        progress.advance()

    return results


def _phase_store_entities(
    entity_results: list[tuple[str, str, list[dict]]],
    progress: PhaseProgress,
) -> None:
    """Phase 4.5: Store extracted entities in the entity index."""
    from caprag.entity_index import EntityIndex

    progress.start_phase("storing_entities", len(entity_results))
    index = EntityIndex()
    try:
        for book, chunk_id, entities in entity_results:
            if entities:
                index.add_entities(book, chunk_id, entities)
            progress.advance()
    finally:
        index.close()
