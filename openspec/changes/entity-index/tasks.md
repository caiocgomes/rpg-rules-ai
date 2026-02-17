## 1. SQLite Entity Index Module

- [ ] 1.1 Create `caprag/entity_index.py` with SQLite schema (entities, entity_mentions tables)
- [ ] 1.2 Implement `EntityIndex` class: `add_entities(book, chunk_id, entities)`, `query_entity(name) -> list[mentions]`, `query_cross_book(entity_names, exclude_book) -> list[mentions]`
- [ ] 1.3 Implement `delete_book_entities(book)` and garbage collection for orphan entities
- [ ] 1.4 Add `ENTITY_INDEX_PATH` to `caprag/config.py` (default `data/entity_index.db`)
- [ ] 1.5 Write tests for CRUD operations, cross-book queries, delete consistency

## 2. Entity Extraction

- [ ] 2.1 Add entity extraction prompt to `caprag/prompts.py`
- [ ] 2.2 Create `caprag/entity_extractor.py` with `extract_entities(parent: Document, book_name: str) -> list[Entity]`
- [ ] 2.3 Implement batch extraction with asyncio.gather (similar to contextualizer)
- [ ] 2.4 Write tests for entity extraction (mocked LLM, structured output parsing)

## 3. Pipeline Integration

- [ ] 3.1 Add entity extraction phase to `caprag/pipeline.py` (after split, can run parallel with contextualization)
- [ ] 3.2 Wire entity insertion into entity index during store phase
- [ ] 3.3 Update `delete_book()` in `caprag/ingest.py` to also clean entity index
- [ ] 3.4 Write integration tests

## 4. Multi-Hop Integration

- [ ] 4.1 Update `caprag/strategies/multi_hop.py`: after each hop, extract entities from retrieved chunks
- [ ] 4.2 Query entity index for cross-book mentions not yet in context
- [ ] 4.3 Generate targeted retrieval queries with Chroma book filter for discovered cross-book entities
- [ ] 4.4 Write tests for cross-book retrieval via entity index

## 5. Validation

- [ ] 5.1 Ingest 2+ books, inspect entity index for quality (defines vs references, cross-book coverage)
- [ ] 5.2 Test cross-book queries: "How does Rapid Strike work?" should retrieve from Basic Set AND Martial Arts
