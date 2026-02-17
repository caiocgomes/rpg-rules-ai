## MODIFIED Requirements

### Requirement: Document upload interface
The system SHALL provide an HTML page where the user can upload multiple markdown files simultaneously and trigger batch ingestion. The interface SHALL also accept a local directory path for ingesting all markdown files from that directory.

#### Scenario: Upload and ingest multiple files
- **WHEN** the user uploads 3 .md files via the file input and clicks the ingest button
- **THEN** all 3 files are sent as multipart POST to the API and processing begins in background

#### Scenario: Ingest from directory path
- **WHEN** the user enters a valid directory path and clicks the ingest button
- **THEN** all .md files in the directory are queued for batch ingestion in background

#### Scenario: Invalid directory path
- **WHEN** the user enters a non-existent directory path and clicks ingest
- **THEN** the system SHALL display an error message without starting any ingestion

### Requirement: List indexed documents
The system SHALL display the list of documents currently indexed in the vector store with metadata including book name and chunk count. Each document SHALL have action buttons for delete and re-index.

#### Scenario: View indexed documents with metadata
- **WHEN** the user navigates to the Documents page
- **THEN** a table of indexed books is displayed showing book name and chunk count for each

#### Scenario: Delete a book from the index
- **WHEN** the user clicks the delete button for a specific book
- **THEN** all chunks for that book are removed from the Chroma collection, the book row disappears from the table, and a confirmation message is shown

#### Scenario: Re-index a specific book
- **WHEN** the user clicks the re-index button for a specific book and the source file exists in `SOURCES_DIR`
- **THEN** the system deletes the existing chunks and re-ingests from the persisted source file with current parameters

#### Scenario: Re-index without source file
- **WHEN** a book's source file is missing from `SOURCES_DIR`
- **THEN** the re-index button SHALL be disabled with a tooltip indicating the source file is unavailable

### Requirement: Background ingestion with progress display
The system SHALL process ingestion in a background thread and display real-time progress in the Documents page without blocking the chat or other pages.

#### Scenario: Progress display during batch ingestion
- **WHEN** a batch of 5 files is being ingested in background
- **THEN** the UI displays: current phase name, phase progress bar, and per-file status (success/skipped/error)

#### Scenario: UI remains interactive during ingestion
- **WHEN** background ingestion is running
- **THEN** the user can navigate to the Chat page and submit questions without waiting for ingestion to finish

#### Scenario: Ingestion completes
- **WHEN** all files in the batch have been processed
- **THEN** the progress display shows a completion summary with per-file status, and the document list updates to reflect new additions

## REMOVED Requirements

### Requirement: Streamlit-based interface
**Reason**: Replaced by Jinja2+HTMX frontend served directly by FastAPI. Streamlit imposed limitations on custom HTML rendering needed for inline citations.
**Migration**: All functionality is replicated in the new Jinja2 templates. Users access the same URL as the API (`localhost:8100`) instead of a separate Streamlit port.
