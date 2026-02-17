## 1. PDF Extraction Module

- [ ] 1.1 Add `pymupdf4llm` to `pyproject.toml`
- [ ] 1.2 Create `caprag/extraction.py` with `extract_pdf(path) -> str`
- [ ] 1.3 Implement `postprocess_headers(md: str) -> str`: bold ALL-CAPS → `##`, italic+bold → `###`
- [ ] 1.4 Implement `clean_page_artifacts(md: str) -> str`: remove page numbers, repeated headers/footers
- [ ] 1.5 Write tests for extraction + header detection on sample PDF pages

## 2. Chunking Module

- [ ] 2.1 Create `caprag/chunking.py` with centralized splitter definitions
- [ ] 2.2 Implement `split_into_sections(md: str) -> List[Document]`: MarkdownHeaderTextSplitter by `##` and `###`
- [ ] 2.3 Implement `split_sections_into_parents(sections: List[Document], max_size: int) -> List[Document]`: sections > max_size get character-split, rest stay whole
- [ ] 2.4 Implement `split_parents_into_children(parents: List[Document]) -> tuple[List[Document], dict[str, Document]]`: child chunks + parent map with doc_id linkage
- [ ] 2.5 Write tests for section splitting, parent splitting (under/over threshold), child splitting, ID consistency

## 3. Settings

- [ ] 3.1 Add `CHILD_CHUNK_SIZE`, `CHILD_CHUNK_OVERLAP`, `PARENT_CHUNK_MAX`, `PARENT_CHUNK_OVERLAP`, `RETRIEVER_K` to `caprag/config.py`
- [ ] 3.2 Update `.env.example` with new settings

## 4. Pipeline Integration

- [ ] 4.1 Update `caprag/pipeline.py` Phase 1 (parse) to detect `.pdf` files and route through `extract_pdf()` + `postprocess_headers()`; `.md` files continue through `UnstructuredMarkdownLoader`
- [ ] 4.2 Update `caprag/pipeline.py` Phase 2 (split) to use `caprag/chunking.py` section-aware splitting
- [ ] 4.3 Update `caprag/retriever.py` to import splitters from `caprag/chunking.py` and use `RETRIEVER_K` from config
- [ ] 4.4 Remove duplicated splitter definitions from `retriever.py` and `pipeline.py`
- [ ] 4.5 Write integration tests for full pipeline with PDF input

## 5. Validation

- [ ] 5.1 Reindex with one PDF (Martial Arts), verify parent chunks respect section boundaries
- [ ] 5.2 Run test queries comparing old vs new chunking quality
- [ ] 5.3 Update `CLAUDE.md` with new chunk sizes and extraction pipeline description
