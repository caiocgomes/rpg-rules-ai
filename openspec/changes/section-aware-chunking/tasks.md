## 1. PDF Extraction Module

- [x] 1.1 Add `pymupdf4llm` to `pyproject.toml`
- [x] 1.2 Create `caprag/extraction.py` with `extract_pdf(path) -> str`
- [x] 1.3 Implement `postprocess_headers(md: str) -> str`: bold ALL-CAPS → `##`, italic+bold → `###`
- [x] 1.4 Implement `clean_page_artifacts(md: str) -> str`: remove page numbers, repeated headers/footers
- [x] 1.5 Write tests for extraction + header detection on sample PDF pages

## 2. Chunking Module

- [x] 2.1 Create `caprag/chunking.py` with centralized splitter definitions
- [x] 2.2 Implement `split_into_sections(md: str) -> List[Document]`: MarkdownHeaderTextSplitter by `##` and `###`
- [x] 2.3 Implement `split_sections_into_parents(sections: List[Document], max_size: int) -> List[Document]`: sections > max_size get character-split, rest stay whole
- [x] 2.4 Implement `split_parents_into_children(parents: List[Document]) -> tuple[List[Document], dict[str, Document]]`: child chunks + parent map with doc_id linkage
- [x] 2.5 Write tests for section splitting, parent splitting (under/over threshold), child splitting, ID consistency

## 3. Settings

- [x] 3.1 Add `CHILD_CHUNK_SIZE`, `CHILD_CHUNK_OVERLAP`, `PARENT_CHUNK_MAX`, `PARENT_CHUNK_OVERLAP`, `RETRIEVER_K` to `caprag/config.py`
- [x] 3.2 Update `.env.example` with new settings

## 4. Pipeline Integration

- [x] 4.1 Update `caprag/pipeline.py` Phase 1 (parse) to detect `.pdf` files and route through `extract_pdf()` + `postprocess_headers()`; `.md` files continue through `UnstructuredMarkdownLoader`
- [x] 4.2 Update `caprag/pipeline.py` Phase 2 (split) to use `caprag/chunking.py` section-aware splitting
- [x] 4.3 Update `caprag/retriever.py` to import splitters from `caprag/chunking.py` and use `RETRIEVER_K` from config
- [x] 4.4 Remove duplicated splitter definitions from `retriever.py` and `pipeline.py`
- [x] 4.5 Write integration tests for full pipeline with PDF input

## 5. Validation

- [x] 5.1 Reindex with one PDF (Martial Arts), verify parent chunks respect section boundaries
- [x] 5.2 Run test queries comparing old vs new chunking quality
- [x] 5.3 Update `CLAUDE.md` with new chunk sizes and extraction pipeline description
