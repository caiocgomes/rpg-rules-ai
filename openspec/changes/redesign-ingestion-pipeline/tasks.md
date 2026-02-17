## 1. Persistent Docstore

- [x] 1.1 Replace `InMemoryStore` with `LocalFileStore` in `caprag/retriever.py`, configured at `data/docstore/`
- [x] 1.2 Add `DOCSTORE_DIR` setting to `caprag/config.py` (default `./data/docstore`)
- [x] 1.3 Update `delete_book()` in `caprag/ingest.py` to also remove parent chunks from the docstore
- [x] 1.4 Add Docker volume for `data/docstore/` in `docker-compose.yml`
- [x] 1.5 Write tests for docstore persistence across retriever re-initialization
- [x] 1.6 Write tests for delete consistency (vectorstore + docstore)

## 2. Multipart Upload Endpoint

- [x] 2.1 Add `POST /documents/upload` endpoint in `caprag/api.py` accepting `UploadFile` list with optional `replace` query param
- [x] 2.2 Endpoint saves files to `data/sources/`, validates `.md` extension, enforces 20MB limit
- [x] 2.3 Endpoint creates `IngestionJob` with saved paths and returns `202` with `job_id`
- [x] 2.4 Write tests for upload endpoint (single file, multiple files, invalid extension, size limit)

## 3. Layered Ingestion Pipeline

- [x] 3.1 Create `caprag/pipeline.py` with layered ingestion function: parse → split → embed → store
- [x] 3.2 Phase 1 (parse): load all files via `UnstructuredMarkdownLoader`, skip failures with error recording
- [x] 3.3 Phase 2 (split): apply `parent_splitter` then `child_splitter` over all parsed docs, generate consistent parent/child ID mapping
- [x] 3.4 Phase 3 (embed): call `OpenAIEmbeddings.embed_documents()` in sub-batches of 500 chunks
- [x] 3.5 Phase 4 (store): insert into Chroma `collection.add()` with pre-computed embeddings in sub-batches of 100, `LocalFileStore.mset()` for parents
- [x] 3.6 Wire progress callback to report phase name, items completed, items total
- [x] 3.7 Write tests for full pipeline (mocked embeddings), error isolation, ID consistency

## 4. Update IngestionJob

- [x] 4.1 Update `caprag/ingestion_job.py` to use the new layered pipeline instead of `ingest_files()`
- [x] 4.2 Update `get_progress()` to return phase-level progress (`phase`, `phase_completed`, `phase_total`)
- [x] 4.3 Update `caprag/schemas.py` with new progress types for phase reporting
- [x] 4.4 Write tests for job progress reporting by phase

## 5. Update Streamlit Frontend

- [x] 5.1 Change upload in `app.py` from writing to `/tmp` + POST paths to multipart POST to `/documents/upload`
- [x] 5.2 Update progress display to show phase-level progress (phase name, phase progress bar, per-file results)
- [x] 5.3 Update directory ingestion to POST paths to existing `/documents/ingest` (directory path remains server-side)
- [ ] 5.4 Manual test: upload files, verify progress phases display, verify chat works during ingestion

## 6. Cleanup and Migration

- [x] 6.1 Remove old `ingest_file()` serial pipeline from `caprag/ingest.py` (replaced by `caprag/pipeline.py`)
- [x] 6.2 Update `reindex_directory()` to use the new layered pipeline
- [x] 6.3 Update `CLAUDE.md` with new architecture description
- [x] 6.4 Update existing tests that mock old ingestion functions
