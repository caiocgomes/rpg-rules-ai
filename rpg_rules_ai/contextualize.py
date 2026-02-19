"""Contextual embedding enrichment: generate context prefixes for child chunks."""

from __future__ import annotations

import asyncio
import logging

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from rpg_rules_ai.prompts import DEFAULT_CONTEXT_TEMPLATE

logger = logging.getLogger(__name__)


async def generate_context(
    parent: Document,
    child: Document,
    book_name: str,
    model: str = "gpt-4o-mini",
) -> str:
    """Generate a context prefix for a child chunk using its parent as context.

    Returns a short (2-3 sentence) description situating the child within the parent.
    """
    llm = ChatOpenAI(model=model, temperature=0)
    prompt = ChatPromptTemplate.from_template(DEFAULT_CONTEXT_TEMPLATE)

    section_headers = child.metadata.get("section_headers", "")
    if not section_headers:
        section_headers = parent.metadata.get("section_headers", "Unknown section")

    messages = await prompt.ainvoke({
        "book_name": book_name,
        "section_headers": section_headers,
        "parent_text": parent.page_content,
        "child_text": child.page_content,
    })

    response = await llm.ainvoke(messages)
    return response.content


async def contextualize_batch(
    parents_and_children: list[tuple[Document, Document, str]],
    model: str = "gpt-4o-mini",
    batch_size: int = 20,
) -> list[str]:
    """Generate context prefixes for a batch of (parent, child, book_name) tuples.

    Processes in sub-batches of `batch_size` concurrent calls to respect rate limits.
    Returns a list of context prefix strings in the same order as input.
    """
    results: list[str] = []

    for i in range(0, len(parents_and_children), batch_size):
        batch = parents_and_children[i : i + batch_size]
        tasks = [
            generate_context(parent, child, book_name, model=model)
            for parent, child, book_name in batch
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.warning(
                    "Context generation failed for chunk %d: %s", i + j, result
                )
                results.append("")
            else:
                results.append(result)

    return results
