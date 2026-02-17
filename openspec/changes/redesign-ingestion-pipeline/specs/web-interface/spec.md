## MODIFIED Requirements

### Requirement: Document upload interface
The system SHALL provide a Streamlit page where the user can upload multiple markdown files simultaneously. The upload SHALL send files directly to the API via multipart POST (not write to local filesystem). The interface SHALL also accept a local directory path for ingesting all markdown files from that directory.

#### Scenario: Upload and ingest multiple files
- **WHEN** the user uploads 3 .md files via the file uploader and clicks the ingest button
- **THEN** all 3 files SHALL be sent to the API as multipart form data, and the API SHALL return a job_id for progress tracking

#### Scenario: Ingest from directory path
- **WHEN** the user enters a valid directory path and clicks the ingest button
- **THEN** all .md files in the directory SHALL be sent to the API for batch ingestion

#### Scenario: Invalid directory path
- **WHEN** the user enters a non-existent directory path and clicks ingest
- **THEN** the system SHALL display an error message without starting any ingestion

### Requirement: Background ingestion with progress display
The system SHALL display ingestion progress by phase (parsing, splitting, embedding, storing) without blocking the UI. The progress display SHALL show the current phase, items completed within the phase, and total items.

#### Scenario: Phase-level progress display
- **WHEN** a batch of files is being ingested and the embedding phase is active
- **THEN** the UI SHALL display: current phase ("Embedding"), progress within phase (e.g., "450/2000 chunks"), and an overall progress indicator

#### Scenario: UI remains interactive during ingestion
- **WHEN** background ingestion is running
- **THEN** the user SHALL be able to switch to the Chat tab and submit questions without waiting for ingestion to finish

#### Scenario: Ingestion completes
- **WHEN** all phases of the pipeline have completed
- **THEN** the progress display SHALL show a completion summary with per-file status, and the indexed documents list SHALL update to reflect new additions
