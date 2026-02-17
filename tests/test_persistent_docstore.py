"""Tests for persistent docstore (LocalFileStore) and delete consistency."""

from unittest.mock import MagicMock, patch

import pytest

import caprag.retriever as retriever_module


@pytest.fixture(autouse=True)
def reset_singletons():
    retriever_module._retriever = None
    retriever_module._vectorstore = None
    retriever_module._docstore = None
    yield
    retriever_module._retriever = None
    retriever_module._vectorstore = None
    retriever_module._docstore = None


class TestDocstorePersistence:
    def test_docstore_uses_local_file_store(self, tmp_path):
        with patch("caprag.retriever.settings") as mock_settings:
            mock_settings.docstore_dir = str(tmp_path / "docstore")
            (tmp_path / "docstore").mkdir()

            store = retriever_module.get_docstore()

        from langchain_classic.storage import LocalFileStore
        assert isinstance(store, LocalFileStore)

    def test_docstore_is_cached(self, tmp_path):
        with patch("caprag.retriever.settings") as mock_settings:
            mock_settings.docstore_dir = str(tmp_path / "docstore")
            (tmp_path / "docstore").mkdir()

            store1 = retriever_module.get_docstore()
            store2 = retriever_module.get_docstore()

        assert store1 is store2

    def test_docstore_data_persists_after_singleton_reset(self, tmp_path):
        docstore_path = tmp_path / "docstore"
        docstore_path.mkdir()

        with patch("caprag.retriever.settings") as mock_settings:
            mock_settings.docstore_dir = str(docstore_path)

            store = retriever_module.get_docstore()
            store.mset([("key1", b"value1"), ("key2", b"value2")])

            # Reset singleton
            retriever_module._docstore = None

            store2 = retriever_module.get_docstore()
            results = list(store2.mget(["key1", "key2"]))

        assert results == [b"value1", b"value2"]


class TestDeleteConsistency:
    def test_delete_book_removes_from_docstore(self):
        mock_vs = MagicMock()
        mock_collection = MagicMock()
        mock_vs._collection = mock_collection
        mock_collection.get.return_value = {
            "metadatas": [
                {"book": "Book.md", "doc_id": "parent-1"},
                {"book": "Book.md", "doc_id": "parent-1"},
                {"book": "Book.md", "doc_id": "parent-2"},
            ]
        }
        mock_collection.count.return_value = 0

        mock_docstore = MagicMock()

        with (
            patch("caprag.ingest.get_vectorstore", return_value=mock_vs),
            patch("caprag.ingest.get_docstore", return_value=mock_docstore),
            patch("caprag.ingest.settings") as mock_settings,
        ):
            mock_settings.sources_dir = "/tmp/fake"
            from caprag.ingest import delete_book
            delete_book("Book.md")

        mock_collection.delete.assert_called_once_with(where={"book": "Book.md"})
        assert mock_docstore.mdelete.call_count == 2  # parent-1 and parent-2

    def test_delete_book_no_parents_still_works(self):
        mock_vs = MagicMock()
        mock_collection = MagicMock()
        mock_vs._collection = mock_collection
        mock_collection.get.return_value = {"metadatas": []}
        mock_collection.count.return_value = 0

        with (
            patch("caprag.ingest.get_vectorstore", return_value=mock_vs),
            patch("caprag.ingest.get_docstore", return_value=MagicMock()),
            patch("caprag.ingest.settings") as mock_settings,
        ):
            mock_settings.sources_dir = "/tmp/fake"
            from caprag.ingest import delete_book
            delete_book("Nonexistent.md")

        mock_collection.delete.assert_called_once()
