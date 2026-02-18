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


@patch("caprag.retriever.get_child_splitter")
@patch("caprag.retriever.get_parent_splitter")
@patch("caprag.retriever.ParentDocumentRetriever")
@patch("caprag.retriever.get_vectorstore")
@patch("caprag.retriever.get_docstore")
def test_get_retriever_creates_instance(mock_get_ds, mock_get_vs, mock_pdr_cls, mock_parent_sp, mock_child_sp):
    mock_vs = MagicMock()
    mock_get_vs.return_value = mock_vs
    mock_get_ds.return_value = MagicMock()
    mock_pdr = MagicMock()
    mock_pdr_cls.return_value = mock_pdr

    result = retriever_module.get_retriever()

    assert result is mock_pdr
    mock_get_vs.assert_called_once()
    mock_child_sp.assert_called_once()
    mock_parent_sp.assert_called_once()
    mock_pdr_cls.assert_called_once()


@patch("caprag.retriever.get_vectorstore")
def test_get_retriever_returns_cached(mock_get_vs):
    sentinel = MagicMock()
    retriever_module._retriever = sentinel

    result = retriever_module.get_retriever()

    assert result is sentinel
    mock_get_vs.assert_not_called()


@patch("caprag.retriever.get_child_splitter")
@patch("caprag.retriever.get_parent_splitter")
@patch("caprag.retriever.ParentDocumentRetriever")
@patch("caprag.retriever.get_vectorstore")
@patch("caprag.retriever.get_docstore")
def test_get_retriever_uses_mmr_search_type(mock_get_ds, mock_get_vs, mock_pdr_cls, mock_parent_sp, mock_child_sp):
    mock_get_vs.return_value = MagicMock()
    mock_get_ds.return_value = MagicMock()
    mock_pdr_cls.return_value = MagicMock()

    retriever_module.get_retriever()

    call_kwargs = mock_pdr_cls.call_args[1]
    assert call_kwargs["search_type"] == "mmr"


@patch("caprag.retriever.get_child_splitter")
@patch("caprag.retriever.get_parent_splitter")
@patch("caprag.retriever.ParentDocumentRetriever")
@patch("caprag.retriever.get_vectorstore")
@patch("caprag.retriever.get_docstore")
def test_get_retriever_passes_search_kwargs_from_config(mock_get_ds, mock_get_vs, mock_pdr_cls, mock_parent_sp, mock_child_sp):
    mock_get_vs.return_value = MagicMock()
    mock_get_ds.return_value = MagicMock()
    mock_pdr_cls.return_value = MagicMock()

    retriever_module.get_retriever()

    call_kwargs = mock_pdr_cls.call_args[1]
    search_kwargs = call_kwargs["search_kwargs"]
    assert search_kwargs["k"] == retriever_module.settings.retriever_k
    assert search_kwargs["fetch_k"] == retriever_module.settings.retriever_fetch_k
    assert search_kwargs["lambda_mult"] == retriever_module.settings.retriever_lambda_mult
