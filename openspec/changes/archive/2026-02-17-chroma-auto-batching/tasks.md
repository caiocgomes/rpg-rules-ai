## 1. BatchedChroma implementation

- [x] 1.1 Create `BatchedChroma(Chroma)` class in `caprag/retriever.py` with `add_texts` override that queries `max_batch_size` and splits into sub-batches
- [x] 1.2 Replace `Chroma(...)` with `BatchedChroma(...)` in `get_vectorstore()`

## 2. Tests

- [x] 2.1 Unit test: add_texts with N <= max_batch_size calls super once
- [x] 2.2 Unit test: add_texts with N > max_batch_size splits into correct number of sub-batches and returns concatenated IDs
- [x] 2.3 Unit test: max_batch_size is queried from client, not hardcoded
