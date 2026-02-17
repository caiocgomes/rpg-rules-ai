## 1. Backend: Source File Persistence

- [x] 1.1 Add `SOURCES_DIR` setting to `caprag/config.py` (default: `./data/sources`), ensure directory is created on startup
- [x] 1.2 Modify `ingest_file()` to copy the source markdown to `SOURCES_DIR/{filename}` during ingestion (new and replace)

## 2. Backend: Document Management

- [x] 2.1 Implement `delete_book(book_name)` in `caprag/ingest.py` using Chroma `_collection.delete(where={"book": book_name})` — does NOT delete the source file
- [x] 2.2 Implement `get_books_metadata()` in `caprag/ingest.py` returning list of dicts with `book`, `chunk_count`, and `has_source` (bool, checks if file exists in `SOURCES_DIR`)
- [x] 2.3 Add `replace: bool = False` parameter to `ingest_file()` — when True, call `delete_book()` before ingesting

## 3. Backend: Batch Ingestion

- [x] 3.1 Create `ingest_files(paths, on_progress, replace)` in `caprag/ingest.py` that iterates paths, calls `ingest_file()` per file, catches per-file exceptions, and invokes `on_progress` callback with status
- [x] 3.2 Create `ingest_directory(directory, on_progress, replace)` that discovers `.md` files and delegates to `ingest_files()`
- [x] 3.3 Define a `ProgressUpdate` dataclass/TypedDict in `caprag/schemas.py` with fields: filename, status (success/skipped/error), completed, total, error_message

## 4. Frontend: Background Processing

- [x] 4.1 Create `IngestionJob` class (or similar) that wraps batch ingestion in a `threading.Thread`, stores progress state in a thread-safe structure, and exposes status/progress/results
- [x] 4.2 Wire `IngestionJob` into `st.session_state` so the UI can poll status across Streamlit re-runs

## 5. Frontend: Documents Tab Redesign

- [x] 5.1 Replace single file uploader with `st.file_uploader(accept_multiple_files=True)` for batch upload
- [x] 5.2 Add directory path text input with ingest button
- [x] 5.3 Add progress display section: progress bar, current file, per-file status log
- [x] 5.4 Replace book list with table showing book name, chunk count, `has_source` indicator, and action buttons (delete, re-index)
- [x] 5.5 Implement delete button handler calling `delete_book()` with confirmation
- [x] 5.6 Implement re-index button handler calling `ingest_file(replace=True)` using source file from `SOURCES_DIR` — disable button when `has_source=False`

## 6. Tests

- [x] 6.1 Unit tests for source file persistence — file copied on ingest, overwritten on replace, preserved on delete
- [x] 6.2 Unit tests for `delete_book()` — delete existing, delete non-existent (idempotent)
- [x] 6.3 Unit tests for `get_books_metadata()` — with books, empty collection, `has_source` field accuracy
- [x] 6.4 Unit tests for `ingest_file(replace=True)` — replace existing, replace non-existent
- [x] 6.5 Unit tests for `ingest_files()` — happy path, partial failure, duplicate handling, progress callback invocation
- [x] 6.6 Unit tests for `ingest_directory()` — valid dir, empty dir, invalid path
