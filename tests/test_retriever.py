from unittest.mock import MagicMock, patch

import pytest

import caprag.retriever as retriever_module


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset module-level singletons between tests."""
    retriever_module._retriever = None
    retriever_module._vectorstore = None
    yield
    retriever_module._retriever = None
    retriever_module._vectorstore = None


@patch("caprag.retriever.OpenAIEmbeddings")
@patch("caprag.retriever.BatchedChroma")
def test_get_vectorstore_creates_instance(mock_chroma_cls, mock_embeddings_cls):
    mock_embeddings = MagicMock()
    mock_embeddings_cls.return_value = mock_embeddings
    mock_vs = MagicMock()
    mock_chroma_cls.return_value = mock_vs

    result = retriever_module.get_vectorstore()

    assert result is mock_vs
    mock_embeddings_cls.assert_called_once()
    mock_chroma_cls.assert_called_once_with(
        collection_name="caprag",
        embedding_function=mock_embeddings,
        persist_directory=retriever_module.settings.chroma_persist_dir,
    )


@patch("caprag.retriever.OpenAIEmbeddings")
@patch("caprag.retriever.BatchedChroma")
def test_get_vectorstore_returns_cached(mock_chroma_cls, mock_embeddings_cls):
    mock_chroma_cls.return_value = MagicMock()
    retriever_module.get_vectorstore()
    retriever_module.get_vectorstore()
    mock_chroma_cls.assert_called_once()


@patch("caprag.retriever.LocalFileStore")
@patch("caprag.retriever.RecursiveCharacterTextSplitter")
@patch("caprag.retriever.ParentDocumentRetriever")
@patch("caprag.retriever.get_vectorstore")
def test_get_retriever_creates_instance(mock_get_vs, mock_pdr_cls, mock_splitter_cls, mock_store_cls):
    mock_vs = MagicMock()
    mock_get_vs.return_value = mock_vs
    mock_store = MagicMock()
    mock_store_cls.return_value = mock_store
    mock_pdr = MagicMock()
    mock_pdr_cls.return_value = mock_pdr

    result = retriever_module.get_retriever()

    assert result is mock_pdr
    mock_get_vs.assert_called_once()
    assert mock_splitter_cls.call_count == 2  # child + parent
    mock_pdr_cls.assert_called_once()


@patch("caprag.retriever.get_vectorstore")
def test_get_retriever_returns_cached(mock_get_vs):
    sentinel = MagicMock()
    retriever_module._retriever = sentinel

    result = retriever_module.get_retriever()

    assert result is sentinel
    mock_get_vs.assert_not_called()
