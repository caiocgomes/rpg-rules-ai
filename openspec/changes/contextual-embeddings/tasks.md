## 1. Context Generation

- [ ] 1.1 Add context prompt template to `caprag/prompts.py` (domain-aware, RPG-specific)
- [ ] 1.2 Create `caprag/contextualize.py` with `generate_context(parent: Document, child: Document, book_name: str) -> str`
- [ ] 1.3 Implement batch contextualizer: `contextualize_batch(parents_and_children: list, model: str, batch_size: int) -> list[str]` with asyncio.gather
- [ ] 1.4 Write tests for context generation (mocked LLM)

## 2. Pipeline Integration

- [ ] 2.1 Add `CONTEXT_MODEL` and `ENABLE_CONTEXTUAL_EMBEDDINGS` to `caprag/config.py`
- [ ] 2.2 Add Phase 2.5 (contextualize) to `caprag/pipeline.py` between split and embed
- [ ] 2.3 Store context_prefix in child metadata, prepend to page_content before embedding
- [ ] 2.4 Update generate node in `caprag/graph.py` to use `metadata.original_text` when available (fallback to page_content)
- [ ] 2.5 Write integration tests for pipeline with contextual embeddings enabled/disabled

## 3. Validation

- [ ] 3.1 Ingest one book with contextual embeddings, inspect context prefixes for quality
- [ ] 3.2 Compare retrieval results with/without contextual embeddings on test queries
