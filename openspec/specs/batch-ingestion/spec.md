## ADDED Requirements

### Requirement: Batch ingestion of multiple files
The system SHALL accept a list of file paths and process each sequentially through the existing ingestion pipeline. Falha em um arquivo SHALL NOT abortar o processamento dos demais. O resultado SHALL incluir status por arquivo (sucesso, skipped por duplicata, ou erro com mensagem).

#### Scenario: Multiple files ingested successfully
- **WHEN** a list of 5 markdown file paths is provided to the batch ingestion pipeline
- **THEN** each file is processed sequentially via `ingest_file()`, and the result contains 5 entries with status "success" and document counts

#### Scenario: Partial failure in batch
- **WHEN** a batch of 3 files is submitted and the second file has a parsing error
- **THEN** the first and third files are ingested successfully, and the result for the second file contains status "error" with the exception message

#### Scenario: Batch with duplicate detection
- **WHEN** a batch contains a file whose book name is already indexed and replace is not enabled
- **THEN** that file is skipped with status "skipped" and the remaining files are processed normally

### Requirement: Directory ingestion
The system SHALL accept a directory path, discover all `.md` files within it (non-recursive), and process them through the batch ingestion pipeline.

#### Scenario: Ingest all markdown files from directory
- **WHEN** a directory path containing 4 `.md` files and 2 `.txt` files is provided
- **THEN** only the 4 `.md` files are queued for batch ingestion; `.txt` files are ignored

#### Scenario: Empty directory
- **WHEN** a directory path containing no `.md` files is provided
- **THEN** the system SHALL return an empty result with zero files processed and no error

#### Scenario: Invalid directory path
- **WHEN** a non-existent directory path is provided
- **THEN** the system SHALL raise a clear error indicating the path does not exist

### Requirement: Progress callback during ingestion
The batch ingestion pipeline SHALL accept an optional progress callback that is invoked after each file completes. O callback SHALL receive: filename, status (success/skipped/error), files completed count, total files count, and error message if applicable.

#### Scenario: Progress updates during batch
- **WHEN** a batch of 3 files is ingested with a progress callback registered
- **THEN** the callback is invoked 3 times, once after each file, with incrementing completed count (1/3, 2/3, 3/3)

### Requirement: Replace mode for duplicate files
The `ingest_file()` function SHALL accept a `replace` parameter. When `replace=True` and a document with the same book name exists, the system SHALL delete the existing document's chunks and re-ingest the new file.

#### Scenario: Replace existing document
- **WHEN** `ingest_file("GURPS Magic.md", replace=True)` is called and "GURPS Magic.md" is already indexed
- **THEN** all chunks with metadata `book="GURPS Magic.md"` are deleted from the Chroma collection, and the new file is ingested in their place

#### Scenario: Replace with no existing document
- **WHEN** `ingest_file("New Book.md", replace=True)` is called and "New Book.md" is not indexed
- **THEN** the file is ingested normally (no delete operation occurs)

### Requirement: Source file persistence
The system SHALL copy each ingested markdown file to a configurable sources directory (`SOURCES_DIR`, default `./data/sources/`). The copy SHALL be created or overwritten during ingestion. This enables re-indexation without requiring the user to re-upload the original file.

#### Scenario: Source file saved on first ingestion
- **WHEN** a file "GURPS Magic.md" is ingested for the first time
- **THEN** a copy of the file SHALL exist at `{SOURCES_DIR}/GURPS Magic.md`

#### Scenario: Source file overwritten on replace
- **WHEN** `ingest_file("GURPS Magic.md", replace=True)` is called with a new version of the file
- **THEN** the copy at `{SOURCES_DIR}/GURPS Magic.md` SHALL be overwritten with the new content

#### Scenario: Source file preserved on delete
- **WHEN** `delete_book("GURPS Magic.md")` removes a book from the index
- **THEN** the source file at `{SOURCES_DIR}/GURPS Magic.md` SHALL NOT be deleted (allows future re-ingestion)
