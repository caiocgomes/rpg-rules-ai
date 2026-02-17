"""Integration tests for the FastAPI API layer."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from caprag.api import app
from caprag import services
from caprag.prompts import PROMPTS_DIR
from caprag.schemas import Question, Questions


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_jobs():
    services._jobs.clear()
    yield
    services._jobs.clear()


# --- Health ---


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- POST /ask ---


def test_ask_returns_answer(client):
    mock_answer = {
        "answer": "Magery costs 5 points per level.",
        "sources": ["Basic Set"],
        "citations": [{"quote": "Magery costs 5 points", "source": "Basic Set"}],
        "see_also": ["Magery 0"],
    }

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value={"answer": mock_answer})

    with patch("caprag.services._get_graph", return_value=mock_graph):
        resp = client.post("/api/ask", json={"question": "How does Magery work?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "Magery costs 5 points per level."
    assert "Basic Set" in data["sources"]


def test_ask_missing_question(client):
    resp = client.post("/api/ask", json={})
    assert resp.status_code == 422


# --- GET /documents ---


def test_list_documents(client):
    mock_meta = [{"book": "Basic Set.md", "chunk_count": 100, "has_source": True}]
    with patch("caprag.services.get_books_metadata", return_value=mock_meta):
        resp = client.get("/api/documents")

    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["book"] == "Basic Set.md"


def test_list_documents_empty(client):
    with patch("caprag.services.get_books_metadata", return_value=[]):
        resp = client.get("/api/documents")

    assert resp.status_code == 200
    assert resp.json() == []


# --- POST /documents/ingest ---


def test_ingest_starts_job(client, tmp_path):
    md = tmp_path / "test.md"
    md.write_text("# Test")

    with patch.object(
        __import__("caprag.ingestion_job", fromlist=["IngestionJob"]).IngestionJob,
        "start",
    ):
        resp = client.post(
            "/api/documents/ingest",
            json={"paths": [str(md)], "replace": False},
        )

    assert resp.status_code == 202
    assert "job_id" in resp.json()


def test_ingest_invalid_path(client):
    resp = client.post(
        "/api/documents/ingest",
        json={"paths": ["/nonexistent/file.md"]},
    )
    assert resp.status_code == 400


# --- GET /documents/jobs/{job_id} ---


def test_job_progress_found(client):
    from caprag.ingestion_job import IngestionJob

    job = IngestionJob(paths=[])
    job._progress["status"] = "done"
    services._jobs["test-id"] = job

    resp = client.get("/api/documents/jobs/test-id")
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


def test_job_progress_not_found(client):
    resp = client.get("/api/documents/jobs/nonexistent")
    assert resp.status_code == 404


# --- DELETE /documents/{book} ---


def test_delete_document(client):
    with patch("caprag.services._delete_book") as mock_del:
        resp = client.delete("/api/documents/BasicSet.md")

    assert resp.status_code == 200
    mock_del.assert_called_once_with("BasicSet.md")


# --- GET /prompts ---


def test_list_prompts(client, monkeypatch, tmp_path):
    monkeypatch.setattr("caprag.services.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("caprag.prompts.PROMPTS_DIR", tmp_path)

    resp = client.get("/api/prompts")
    assert resp.status_code == 200
    data = resp.json()
    names = {p["name"] for p in data}
    assert "rag" in names
    assert "multi_question" in names
    for p in data:
        assert "content" in p
        assert "variables" in p
        assert p["is_custom"] is False


def test_list_prompts_with_custom(client, monkeypatch, tmp_path):
    monkeypatch.setattr("caprag.services.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("caprag.prompts.PROMPTS_DIR", tmp_path)
    (tmp_path / "rag.txt").write_text("custom prompt {question} {context}")

    resp = client.get("/api/prompts")
    data = resp.json()
    rag = next(p for p in data if p["name"] == "rag")
    assert rag["is_custom"] is True
    assert "custom prompt" in rag["content"]


# --- GET /prompts/{name} ---


def test_get_prompt(client, monkeypatch, tmp_path):
    monkeypatch.setattr("caprag.services.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("caprag.prompts.PROMPTS_DIR", tmp_path)

    resp = client.get("/api/prompts/rag")
    assert resp.status_code == 200
    assert resp.json()["name"] == "rag"
    assert "question" in resp.json()["variables"]


def test_get_prompt_not_found(client):
    resp = client.get("/api/prompts/nonexistent")
    assert resp.status_code == 404


# --- PUT /prompts/{name} ---


def test_update_prompt(client, monkeypatch, tmp_path):
    monkeypatch.setattr("caprag.prompts.PROMPTS_DIR", tmp_path)

    resp = client.put(
        "/api/prompts/rag",
        json={"content": "new prompt {question} {context}"},
    )
    assert resp.status_code == 200
    assert (tmp_path / "rag.txt").read_text() == "new prompt {question} {context}"


def test_update_prompt_not_found(client):
    resp = client.put("/api/prompts/nonexistent", json={"content": "x"})
    assert resp.status_code == 404


# --- DELETE /prompts/{name} ---


def test_reset_prompt(client, monkeypatch, tmp_path):
    monkeypatch.setattr("caprag.services.PROMPTS_DIR", tmp_path)
    monkeypatch.setattr("caprag.prompts.PROMPTS_DIR", tmp_path)
    (tmp_path / "rag.txt").write_text("custom")

    resp = client.delete("/api/prompts/rag")
    assert resp.status_code == 200
    assert resp.json()["is_default"] is True
    assert not (tmp_path / "rag.txt").exists()


def test_reset_prompt_not_found(client):
    resp = client.delete("/api/prompts/nonexistent")
    assert resp.status_code == 404
