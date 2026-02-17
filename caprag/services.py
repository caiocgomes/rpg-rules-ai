"""Centralized service layer for CapaRAG.

Owns the graph singleton and job registry. Both api.py and frontend.py
delegate here instead of maintaining their own state.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from caprag.ingest import delete_book as _delete_book
from caprag.ingest import get_books_metadata
from caprag.ingestion_job import IngestionJob
from caprag.prompts import (
    PROMPT_CONFIGS,
    PROMPTS_DIR,
    get_prompt_content,
    reset_prompt as _reset_prompt,
    save_prompt as _save_prompt,
)

_graph = None
_jobs: dict[str, IngestionJob] = {}


def _get_graph():
    global _graph
    if _graph is None:
        from caprag.graph import build_graph

        _graph = build_graph()
    return _graph


# --- Chat ---


async def ask_question(question: str) -> dict:
    graph = _get_graph()
    result = await graph.ainvoke(
        {"messages": {"role": "user", "content": question}},
    )
    return result["answer"]


# --- Documents ---


def validate_upload_paths(paths: list[Path]) -> None:
    for p in paths:
        if not p.name.endswith(".md"):
            raise ValueError(f"Only .md files are accepted, got: {p.name}")


def create_ingestion_job(paths: list[Path], replace: bool = False) -> str:
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(f"Path not found: {p}")
    job_id = str(uuid.uuid4())
    job = IngestionJob(paths=paths, replace=replace)
    _jobs[job_id] = job
    job.start()
    return job_id


def get_job_progress(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise KeyError(f"Job not found: {job_id}")
    return job.get_progress()


def list_books() -> list[dict]:
    return get_books_metadata()


def delete_book(book: str) -> None:
    _delete_book(book)


# --- Prompts ---


def _validate_prompt_name(name: str) -> None:
    if name not in PROMPT_CONFIGS:
        raise KeyError(f"Prompt not found: {name}")


def list_prompts() -> list[dict]:
    result = []
    for name, config in PROMPT_CONFIGS.items():
        local_path = PROMPTS_DIR / config["file"]
        result.append(
            {
                "name": name,
                "content": get_prompt_content(name),
                "variables": config["variables"],
                "is_custom": local_path.exists(),
            }
        )
    return result


def get_prompt(name: str) -> dict:
    _validate_prompt_name(name)
    config = PROMPT_CONFIGS[name]
    local_path = PROMPTS_DIR / config["file"]
    return {
        "name": name,
        "content": get_prompt_content(name),
        "variables": config["variables"],
        "is_custom": local_path.exists(),
    }


def save_prompt(name: str, content: str) -> None:
    _validate_prompt_name(name)
    _save_prompt(name, content)


def reset_prompt(name: str) -> dict:
    _validate_prompt_name(name)
    _reset_prompt(name)
    return {
        "name": name,
        "content": get_prompt_content(name),
        "is_default": True,
    }
