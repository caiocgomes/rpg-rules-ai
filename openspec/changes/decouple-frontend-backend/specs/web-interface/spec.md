## MODIFIED Requirements

### Requirement: Document upload interface
The system SHALL provide a page where the user can upload multiple markdown files simultaneously and trigger batch ingestion. The interface SHALL also accept a local directory path for ingesting all markdown files from that directory. Upload handling (receiving `UploadFile`, saving to disk) remains in the router; all business logic (job creation, validation, progress tracking) SHALL be delegated to the service layer.

#### Scenario: Upload and ingest multiple files
- **WHEN** the user uploads 3 .md files via the file uploader and clicks the ingest button
- **THEN** the router saves files to disk, calls `services.create_ingestion_job()` with the saved paths, and returns progress HTML

#### Scenario: Ingest from directory path
- **WHEN** the user enters a valid directory path and clicks the ingest button
- **THEN** the router calls `services.create_ingestion_job()` with the discovered .md file paths and returns progress HTML

#### Scenario: Invalid directory path
- **WHEN** the user enters a non-existent directory path and clicks ingest
- **THEN** the system SHALL display an error message without starting any ingestion

### Requirement: List indexed documents
The system SHALL display the list of documents currently indexed in the vector store with metadata including book name and chunk count. Each document SHALL have action buttons for delete and re-index. The data retrieval SHALL be delegated to `services.list_books()`.

#### Scenario: View indexed documents with metadata
- **WHEN** the user navigates to the Documents tab
- **THEN** a table of indexed books is displayed showing book name and chunk count for each, retrieved via the service layer

#### Scenario: Delete a book from the index
- **WHEN** the user clicks the delete button for a specific book
- **THEN** `services.delete_book()` is called, all chunks for that book are removed, and the list refreshes

#### Scenario: Re-index a specific book
- **WHEN** the user clicks the re-index button for a specific book and the source file exists in `SOURCES_DIR`
- **THEN** the system deletes the existing chunks and re-ingests from the persisted source file with current parameters

#### Scenario: Re-index without source file
- **WHEN** the user clicks the re-index button for a book whose source file is missing from `SOURCES_DIR`
- **THEN** the re-index button SHALL be disabled or display a message indicating the source file is unavailable and the user needs to re-upload

### Requirement: Background ingestion with progress display
The system SHALL process ingestion in a background thread and display real-time progress in the Documents tab without blocking the chat or other UI interactions. Progress polling SHALL call `services.get_job_progress()` instead of accessing a local job registry.

#### Scenario: Progress display during batch ingestion
- **WHEN** a batch of 5 files is being ingested in background
- **THEN** the UI displays: current file being processed, number of files completed vs total, status of each completed file (success/skipped/error), and an overall progress bar

#### Scenario: UI remains interactive during ingestion
- **WHEN** background ingestion is running
- **THEN** the user can switch to the Chat tab and submit questions without waiting for ingestion to finish

#### Scenario: Ingestion completes
- **WHEN** all files in the batch have been processed
- **THEN** the progress display shows a completion summary with per-file status, and the indexed documents list updates to reflect new additions
