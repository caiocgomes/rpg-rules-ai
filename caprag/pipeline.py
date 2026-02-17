"""Layered ingestion pipeline: parse → split → embed → store."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

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

        # Phase 3: Embed
        embeddings = _phase_embed(child_chunks, progress)

        # Phase 4: Store
        _phase_store(child_chunks, embeddings, parent_map, progress)

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
    """Phase 1: Parse all markdown files."""
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
    """Phase 2: Split into parent and child chunks with ID mapping."""
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000, chunk_overlap=400, add_start_index=True
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200, chunk_overlap=40, add_start_index=True
    )

    parent_chunks = parent_splitter.split_documents(docs)
    progress.start_phase("splitting", len(parent_chunks))

    child_chunks: list[Document] = []
    parent_map: dict[str, Document] = {}

    for parent in parent_chunks:
        parent_id = str(uuid.uuid4())
        parent_map[parent_id] = parent

        children = child_splitter.split_documents([parent])
        for child in children:
            child.metadata["doc_id"] = parent_id
        child_chunks.extend(children)
        progress.advance()

    return parent_chunks, child_chunks, parent_map


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
