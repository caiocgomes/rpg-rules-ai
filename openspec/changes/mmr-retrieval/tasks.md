## 1. Retriever Configuration

- [x] 1.1 Add `RETRIEVER_FETCH_K` (default 30) and `RETRIEVER_LAMBDA_MULT` (default 0.7) to `caprag/config.py`
- [x] 1.2 Update `get_retriever()` in `caprag/retriever.py`: add `search_type="mmr"` and `search_kwargs={"k": RETRIEVER_K, "fetch_k": RETRIEVER_FETCH_K, "lambda_mult": RETRIEVER_LAMBDA_MULT}`
- [x] 1.3 Update `.env.example` with new settings

## 2. Testing

- [x] 2.1 Write test verifying retriever is configured with MMR search type
- [x] 2.2 Write test verifying search_kwargs are passed correctly from config
- [ ] 2.3 Manual test: run query and verify results come from multiple books

## 3. Documentation

- [x] 3.1 Update `CLAUDE.md` retriever section with MMR configuration
