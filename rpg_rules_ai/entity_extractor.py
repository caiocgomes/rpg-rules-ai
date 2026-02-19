"""Entity extraction from parent chunks via LLM structured output."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from rpg_rules_ai.prompts import DEFAULT_ENTITY_EXTRACTION_TEMPLATE

logger = logging.getLogger(__name__)


class ExtractedEntity(BaseModel):
    name: str = Field(description="Exact entity name as written in text")
    type: str = Field(description="Entity type: advantage, disadvantage, skill, technique, maneuver, spell, equipment, modifier, other")
    mention_type: str = Field(description="'defines' if passage explains the entity, 'references' if it just mentions it")


class ExtractedEntities(BaseModel):
    entities: List[ExtractedEntity] = Field(default_factory=list, description="List of extracted entities")


async def extract_entities(
    parent: Document,
    book_name: str,
    model: str = "gpt-4o-mini",
) -> list[dict]:
    """Extract GURPS entities from a parent chunk.

    Returns a list of dicts with keys: name, type, mention_type.
    """
    llm = ChatOpenAI(model=model, temperature=0)
    prompt = ChatPromptTemplate.from_template(DEFAULT_ENTITY_EXTRACTION_TEMPLATE)
    chain = prompt | llm.with_structured_output(ExtractedEntities)

    result = await chain.ainvoke({
        "book_name": book_name,
        "parent_text": parent.page_content,
    })

    return [e.model_dump() for e in result.entities]


async def extract_entities_batch(
    parents: list[tuple[Document, str]],
    model: str = "gpt-4o-mini",
    batch_size: int = 20,
) -> list[list[dict]]:
    """Extract entities from a batch of (parent, book_name) tuples.

    Processes in sub-batches to respect rate limits.
    Returns a list of entity lists in the same order as input.
    """
    results: list[list[dict]] = []

    for i in range(0, len(parents), batch_size):
        batch = parents[i : i + batch_size]
        tasks = [
            extract_entities(parent, book_name, model=model)
            for parent, book_name in batch
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.warning(
                    "Entity extraction failed for chunk %d: %s", i + j, result
                )
                results.append([])
            else:
                results.append(result)

    return results
