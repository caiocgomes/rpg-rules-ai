## MODIFIED Requirements

### Requirement: Document upload interface
The system SHALL provide a Streamlit page where the user can upload multiple markdown files simultaneously and trigger batch ingestion. The interface SHALL also accept a local directory path for ingesting all markdown files from that directory. All operations SHALL be executed via HTTP requests to the API (`POST /documents/ingest`), not via direct module imports.

#### Scenario: Upload and ingest multiple files
- **WHEN** the user uploads 3 .md files via the file uploader and clicks the ingest button
- **THEN** the Streamlit app sends `POST /documents/ingest` to the API and polls `GET /documents/jobs/{id}` for progress

#### Scenario: Ingest from directory path
- **WHEN** the user enters a valid directory path and clicks the ingest button
- **THEN** the Streamlit app sends `POST /documents/ingest` with the directory path to the API

#### Scenario: Invalid directory path
- **WHEN** the user enters a non-existent directory path and clicks ingest
- **THEN** the API returns 400 and the Streamlit app displays the error message

### Requirement: List indexed documents
The system SHALL display the list of documents currently indexed in the vector store with metadata including book name and chunk count. Each document SHALL have action buttons for delete and re-index. Data SHALL be fetched via `GET /documents` from the API.

#### Scenario: View indexed documents with metadata
- **WHEN** the user navigates to the Documents tab
- **THEN** the Streamlit app fetches `GET /documents` and displays a table of indexed books

#### Scenario: Delete a book from the index
- **WHEN** the user clicks the delete button for a specific book
- **THEN** the Streamlit app sends `DELETE /documents/{book}` to the API

#### Scenario: Re-index a specific book
- **WHEN** the user clicks the re-index button for a specific book and the source file exists
- **THEN** the Streamlit app sends `POST /documents/ingest` with replace=true to the API

### Requirement: Background ingestion with progress display
The system SHALL display real-time progress by polling the API's `GET /documents/jobs/{id}` endpoint without blocking the chat or other UI interactions.

#### Scenario: Progress display during batch ingestion
- **WHEN** a batch of 5 files is being ingested in background
- **THEN** the UI polls the API progress endpoint and displays: current file, completed vs total, per-file status, and progress bar

#### Scenario: UI remains interactive during ingestion
- **WHEN** background ingestion is running
- **THEN** the user can switch to the Chat tab and submit questions without waiting

## ADDED Requirements

### Requirement: Zero backend imports
The Streamlit app (`app.py`) SHALL NOT import any module from `caprag.*`. All communication with the backend SHALL happen via HTTP requests to the API.

#### Scenario: App imports
- **WHEN** inspecting `app.py` imports
- **THEN** no `from caprag` or `import caprag` statements exist

### Requirement: Chat via API
The Streamlit chat tab SHALL send questions via `POST /ask` to the API and render the structured response.

#### Scenario: Ask a question
- **WHEN** the user types a question and submits
- **THEN** the Streamlit app sends `POST /ask` with the question and renders the answer, sources, citations, and see_also from the response

### Requirement: Prompts management via API
The Streamlit prompts tab SHALL manage prompts via the API endpoints (`GET /prompts`, `PUT /prompts/{name}`, `DELETE /prompts/{name}`).

#### Scenario: Edit and save prompt
- **WHEN** the user edits a prompt and clicks Save
- **THEN** the Streamlit app sends `PUT /prompts/{name}` to the API

#### Scenario: Reset prompt
- **WHEN** the user clicks Reset
- **THEN** the Streamlit app sends `DELETE /prompts/{name}` to the API and displays the returned default
