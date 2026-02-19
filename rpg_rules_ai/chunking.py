"""Centralized chunking: section-aware hierarchical splitting."""

from __future__ import annotations

import uuid

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from rpg_rules_ai.config import settings


def get_child_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.child_chunk_size,
        chunk_overlap=settings.child_chunk_overlap,
        add_start_index=True,
    )


def get_parent_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.parent_chunk_max,
        chunk_overlap=settings.parent_chunk_overlap,
        add_start_index=True,
    )


def split_into_sections(md: str) -> list[Document]:
    """Split markdown into sections by ## and ### headers.

    Each section Document gets metadata with section_headers showing the hierarchy.
    """
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("##", "h2"),
            ("###", "h3"),
        ],
        strip_headers=False,
    )
    return splitter.split_text(md)


def split_sections_into_parents(
    sections: list[Document],
    max_size: int | None = None,
) -> list[Document]:
    """Split sections into parent chunks.

    Sections smaller than max_size stay whole. Larger sections are character-split.
    Metadata from the original section is preserved on all resulting chunks.
    """
    if max_size is None:
        max_size = settings.parent_chunk_max

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_size,
        chunk_overlap=settings.parent_chunk_overlap,
        add_start_index=True,
    )

    parents: list[Document] = []
    for section in sections:
        if len(section.page_content) <= max_size:
            parents.append(section)
        else:
            sub_chunks = char_splitter.split_documents([section])
            parents.extend(sub_chunks)

    return parents


def split_parents_into_children(
    parents: list[Document],
) -> tuple[list[Document], dict[str, Document]]:
    """Split parent chunks into child chunks with doc_id linkage.

    Returns (child_chunks, parent_map) where parent_map maps parent_id -> parent Document.
    Each child gets metadata["doc_id"] pointing to its parent.
    """
    child_splitter = get_child_splitter()

    child_chunks: list[Document] = []
    parent_map: dict[str, Document] = {}

    for parent in parents:
        parent_id = str(uuid.uuid4())
        parent.metadata["doc_id"] = parent_id
        parent_map[parent_id] = parent

        children = child_splitter.split_documents([parent])
        for child in children:
            child.metadata["doc_id"] = parent_id
        child_chunks.extend(children)

    return child_chunks, parent_map
