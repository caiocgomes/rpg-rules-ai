"""Tests for BatchedChroma auto-batching behavior."""

from unittest.mock import MagicMock, patch

import pytest

from caprag.retriever import CHROMA_BATCH_LIMIT, BatchedChroma


@pytest.fixture
def batched_chroma():
    """Create a BatchedChroma with mocked client."""
    with patch.object(BatchedChroma, "__init__", lambda self, **kw: None):
        bc = BatchedChroma.__new__(BatchedChroma)
        bc._client = MagicMock()
        yield bc


class TestBatchedChroma:
    def test_within_limit_calls_super_once(self, batched_chroma):
        texts = [f"text_{i}" for i in range(50)]
        metadatas = [{"k": str(i)} for i in range(50)]
        ids = [f"id_{i}" for i in range(50)]

        with patch.object(
            BatchedChroma.__bases__[0], "add_texts", return_value=ids
        ) as mock_super:
            result = batched_chroma.add_texts(texts, metadatas=metadatas, ids=ids)

        mock_super.assert_called_once()
        assert result == ids

    def test_exceeding_limit_splits_correctly(self, batched_chroma):
        call_sizes = []
        n_texts = CHROMA_BATCH_LIMIT * 2 + 30
        texts = [f"text_{i}" for i in range(n_texts)]
        metadatas = [{"k": str(i)} for i in range(n_texts)]
        ids = [f"id_{i}" for i in range(n_texts)]

        def fake_add_texts(self, texts, metadatas=None, ids=None, **kw):
            n = len(list(texts))
            call_sizes.append(n)
            return ids[:n] if ids else [f"gen_{i}" for i in range(n)]

        with patch.object(BatchedChroma.__bases__[0], "add_texts", fake_add_texts):
            result = batched_chroma.add_texts(texts, metadatas=metadatas, ids=ids)

        assert call_sizes == [CHROMA_BATCH_LIMIT, CHROMA_BATCH_LIMIT, 30]
        assert result == ids

    def test_empty_texts_returns_empty(self, batched_chroma):
        result = batched_chroma.add_texts([])
        assert result == []
