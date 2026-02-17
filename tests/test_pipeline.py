"""Tests for the layered ingestion pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_md(tmp_path: Path, name: str, content: str = "# Test\nSome content here.") -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


@pytest.fixture
def mock_infra():
    """Mock vectorstore, docstore, embeddings, and settings."""
    mock_vs = MagicMock()
    mock_collection = MagicMock()
    mock_vs._collection = mock_collection
    mock_collection.count.return_value = 0

    mock_docstore = MagicMock()

    mock_embedder = MagicMock()
    mock_embedder.embed_documents.side_effect = lambda texts: [[0.1] * 10 for _ in texts]

    with (
        patch("caprag.pipeline.get_vectorstore", return_value=mock_vs),
        patch("caprag.pipeline.get_docstore", return_value=mock_docstore),
        patch("caprag.pipeline.OpenAIEmbeddings", return_value=mock_embedder),
        patch("caprag.ingest.get_vectorstore", return_value=mock_vs),
        patch("caprag.ingest.get_docstore", return_value=mock_docstore),
        patch("caprag.ingest.settings") as mock_ingest_settings,
        patch("caprag.pipeline.settings") as mock_pipeline_settings,
    ):
        mock_ingest_settings.sources_dir = "/tmp/fake_sources"
        mock_pipeline_settings.embedding_model = "text-embedding-3-large"
        yield {
            "vs": mock_vs,
            "collection": mock_collection,
            "docstore": mock_docstore,
            "embedder": mock_embedder,
        }


class TestLayeredPipeline:
    def test_full_pipeline(self, tmp_path, mock_infra):
        files = [_make_md(tmp_path, f"Book{i}.md", f"# Book {i}\nContent for book {i}.") for i in range(3)]

        from caprag.pipeline import run_layered_pipeline
        result = run_layered_pipeline(files)

        assert result["status"] == "done"
        assert len(result["file_results"]) == 3
        assert all(r["status"] == "success" for r in result["file_results"])
        assert mock_infra["collection"].add.called
        assert mock_infra["docstore"].mset.called

    def test_parse_error_isolation(self, tmp_path, mock_infra):
        good1 = _make_md(tmp_path, "Good1.md")
        good2 = _make_md(tmp_path, "Good2.md")
        bad = _make_md(tmp_path, "Bad.md")

        call_count = 0
        original_loader = None

        def mock_loader_factory(path):
            nonlocal call_count
            call_count += 1
            if "Bad.md" in str(path):
                loader = MagicMock()
                loader.load.side_effect = ValueError("Parse failed")
                return loader
            from langchain_community.document_loaders import UnstructuredMarkdownLoader
            return UnstructuredMarkdownLoader(path)

        with patch("caprag.pipeline.UnstructuredMarkdownLoader", side_effect=mock_loader_factory):
            from caprag.pipeline import run_layered_pipeline
            result = run_layered_pipeline([good1, bad, good2])

        assert result["status"] == "done"
        statuses = {r["filename"]: r["status"] for r in result["file_results"]}
        assert statuses["Good1.md"] == "success"
        assert statuses["Bad.md"] == "error"
        assert statuses["Good2.md"] == "success"

    def test_progress_phases(self, tmp_path, mock_infra):
        files = [_make_md(tmp_path, "Test.md", "# Test\nSome content.")]
        phases_seen = []

        def on_progress(data):
            if data["phase"] and data["phase"] not in phases_seen:
                phases_seen.append(data["phase"])

        from caprag.pipeline import run_layered_pipeline
        run_layered_pipeline(files, on_progress=on_progress)

        assert "parsing" in phases_seen
        assert "splitting" in phases_seen
        assert "embedding" in phases_seen
        assert "storing" in phases_seen

    def test_id_consistency(self, tmp_path, mock_infra):
        files = [_make_md(tmp_path, "Book.md", "# Big Book\n" + "Content. " * 200)]

        from caprag.pipeline import run_layered_pipeline
        run_layered_pipeline(files)

        # Check that collection.add was called with metadatas containing doc_id
        add_calls = mock_infra["collection"].add.call_args_list
        all_doc_ids = set()
        for call in add_calls:
            for meta in call.kwargs.get("metadatas", call[1].get("metadatas", [])):
                if "doc_id" in meta:
                    all_doc_ids.add(meta["doc_id"])

        # Check that docstore.mset was called with matching parent IDs
        mset_calls = mock_infra["docstore"].mset.call_args_list
        parent_ids = set()
        for call in mset_calls:
            for pid, _ in call[0][0]:
                parent_ids.add(pid)

        # All doc_ids in children should exist as parent IDs
        assert all_doc_ids
        assert all_doc_ids.issubset(parent_ids)

    def test_skip_duplicates(self, tmp_path, mock_infra):
        mock_infra["collection"].get.return_value = {"metadatas": [{"book": "Dup.md"}]}
        mock_infra["collection"].count.return_value = 1

        files = [_make_md(tmp_path, "Dup.md")]

        from caprag.pipeline import run_layered_pipeline
        result = run_layered_pipeline(files)

        assert result["status"] == "done"
        assert result["file_results"][0]["status"] == "skipped"
