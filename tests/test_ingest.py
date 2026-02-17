"""Tests for ingest module: delete_book, metadata, indexed books, reindex."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _setup_collection_metadatas(vs, metadatas):
    """Configure mock vectorstore's _collection to return metadatas via paginated get()."""
    vs._collection.count.return_value = len(metadatas)
    vs._collection.get.return_value = {"metadatas": metadatas}


@pytest.fixture
def tmp_sources(tmp_path):
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()
    with patch("caprag.ingest.settings") as mock_settings:
        mock_settings.sources_dir = str(sources_dir)
        yield sources_dir, mock_settings


@pytest.fixture
def mock_vectorstore():
    vs = MagicMock()
    vs._collection = MagicMock()
    _setup_collection_metadatas(vs, [])
    return vs


class TestDeleteBook:
    def test_delete_existing(self, mock_vectorstore):
        mock_vectorstore._collection.get.return_value = {
            "metadatas": [{"book": "Magic.md", "doc_id": "p1"}]
        }
        mock_docstore = MagicMock()

        with (
            patch("caprag.ingest.get_vectorstore", return_value=mock_vectorstore),
            patch("caprag.ingest.get_docstore", return_value=mock_docstore),
        ):
            from caprag.ingest import delete_book
            delete_book("Magic.md")

        mock_vectorstore._collection.delete.assert_called_once_with(where={"book": "Magic.md"})
        mock_docstore.mdelete.assert_called_once_with(["p1"])

    def test_delete_nonexistent_idempotent(self, mock_vectorstore):
        mock_vectorstore._collection.get.return_value = {"metadatas": []}

        with (
            patch("caprag.ingest.get_vectorstore", return_value=mock_vectorstore),
            patch("caprag.ingest.get_docstore", return_value=MagicMock()),
        ):
            from caprag.ingest import delete_book
            delete_book("Nonexistent.md")

        mock_vectorstore._collection.delete.assert_called_once()


class TestGetBooksMetadata:
    def test_with_books(self, tmp_sources, mock_vectorstore):
        sources_dir, _ = tmp_sources
        _setup_collection_metadatas(mock_vectorstore, [
            {"book": "Basic.md"},
            {"book": "Basic.md"},
            {"book": "Magic.md"},
        ])
        (sources_dir / "Basic.md").write_text("x")

        with patch("caprag.ingest.get_vectorstore", return_value=mock_vectorstore):
            from caprag.ingest import get_books_metadata
            result = get_books_metadata()

        assert len(result) == 2
        basic = next(r for r in result if r["book"] == "Basic.md")
        magic = next(r for r in result if r["book"] == "Magic.md")
        assert basic["chunk_count"] == 2
        assert basic["has_source"] is True
        assert magic["chunk_count"] == 1
        assert magic["has_source"] is False

    def test_empty_collection(self, tmp_sources, mock_vectorstore):
        with patch("caprag.ingest.get_vectorstore", return_value=mock_vectorstore):
            from caprag.ingest import get_books_metadata
            result = get_books_metadata()
        assert result == []

    def test_has_source_accuracy(self, tmp_sources, mock_vectorstore):
        sources_dir, _ = tmp_sources
        _setup_collection_metadatas(mock_vectorstore, [{"book": "A.md"}, {"book": "B.md"}])
        (sources_dir / "A.md").write_text("x")

        with patch("caprag.ingest.get_vectorstore", return_value=mock_vectorstore):
            from caprag.ingest import get_books_metadata
            result = get_books_metadata()

        a = next(r for r in result if r["book"] == "A.md")
        b = next(r for r in result if r["book"] == "B.md")
        assert a["has_source"] is True
        assert b["has_source"] is False


class TestGetIndexedBooks:
    def test_returns_sorted_books(self, mock_vectorstore):
        _setup_collection_metadatas(mock_vectorstore, [
            {"book": "Z.md"}, {"book": "A.md"}, {"book": "A.md"},
        ])

        with patch("caprag.ingest.get_vectorstore", return_value=mock_vectorstore):
            from caprag.ingest import get_indexed_books
            result = get_indexed_books()

        assert result == ["A.md", "Z.md"]

    def test_empty_collection(self, mock_vectorstore):
        with patch("caprag.ingest.get_vectorstore", return_value=mock_vectorstore):
            from caprag.ingest import get_indexed_books
            result = get_indexed_books()
        assert result == []


class TestReindexDirectory:
    def test_reindex_clears_and_uses_pipeline(self, tmp_path, mock_vectorstore):
        (tmp_path / "A.md").write_text("# A")
        (tmp_path / "B.md").write_text("# B")

        with (
            patch("caprag.ingest.get_vectorstore", return_value=mock_vectorstore),
            patch("caprag.pipeline.run_layered_pipeline") as mock_pipeline,
        ):
            mock_pipeline.return_value = {
                "status": "done",
                "file_results": [
                    {"filename": "A.md", "status": "success", "error_message": None},
                    {"filename": "B.md", "status": "success", "error_message": None},
                ],
            }
            from caprag.ingest import reindex_directory
            total = reindex_directory(tmp_path)

        assert total == 2
        mock_vectorstore.reset_collection.assert_called_once()
        mock_pipeline.assert_called_once()

    def test_reindex_empty_dir(self, tmp_path, mock_vectorstore):
        with (
            patch("caprag.ingest.get_vectorstore", return_value=mock_vectorstore),
            patch("caprag.pipeline.run_layered_pipeline") as mock_pipeline,
        ):
            mock_pipeline.return_value = {"status": "done", "file_results": []}
            from caprag.ingest import reindex_directory
            total = reindex_directory(tmp_path)

        assert total == 0
        mock_vectorstore.reset_collection.assert_called_once()

    def test_invalid_path(self, tmp_path):
        from caprag.ingest import reindex_directory
        with pytest.raises(FileNotFoundError):
            reindex_directory(tmp_path / "nonexistent")
