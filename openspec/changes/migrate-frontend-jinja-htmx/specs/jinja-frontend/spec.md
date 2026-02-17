## ADDED Requirements

### Requirement: Jinja2 template rendering via FastAPI
The FastAPI application SHALL serve HTML pages using Jinja2 templates from a `caprag/templates/` directory. Static assets (CSS, JS) SHALL be served from `caprag/static/`. The application SHALL use a single base template with navigation between three pages: Chat, Documents, and Prompts.

#### Scenario: Base template with navigation
- **WHEN** the user accesses `http://localhost:8100/`
- **THEN** the browser renders an HTML page with navigation links to Chat (`/`), Documents (`/documents`), and Prompts (`/prompts`)

#### Scenario: Static assets served
- **WHEN** the browser requests `/static/style.css` or `/static/htmx.min.js`
- **THEN** FastAPI serves the file from `caprag/static/` with appropriate content type

### Requirement: Chat page with HTMX
The chat page SHALL display a message history and a text input. Submitting a question SHALL send an HTMX POST request to a server endpoint that returns the rendered answer HTML fragment. The page SHALL NOT do a full reload on submit.

#### Scenario: Submit question and receive answer
- **WHEN** the user types a question and submits the form
- **THEN** HTMX sends a POST to `/chat/ask`, the server returns an HTML fragment with the answer, and HTMX inserts it into the message list without full page reload

#### Scenario: Loading state during question processing
- **WHEN** the user submits a question
- **THEN** a loading indicator is visible until the answer HTML fragment is received and inserted

#### Scenario: Message history persists within session
- **WHEN** the user submits multiple questions in sequence
- **THEN** all previous questions and answers remain visible in the chat area

### Requirement: Documents page with HTMX
The documents page SHALL provide file upload, directory ingestion, progress display, and document list management. All interactions SHALL use HTMX to update page sections without full reload.

#### Scenario: Upload files via multipart form
- **WHEN** the user selects .md files and clicks the upload button
- **THEN** HTMX sends a multipart POST to `/documents/upload`, receives a job_id, and begins polling for progress

#### Scenario: Ingestion progress polling
- **WHEN** an ingestion job is running
- **THEN** HTMX polls `/documents/jobs/{job_id}` at regular intervals and updates the progress section with phase name, progress bar, and per-file results

#### Scenario: Delete document via HTMX
- **WHEN** the user clicks the delete button for a document
- **THEN** HTMX sends a DELETE request to `/documents/{book}` and removes the document row from the list without full page reload

#### Scenario: Re-index document
- **WHEN** the user clicks re-index on a document with available source file
- **THEN** HTMX triggers a POST to `/documents/ingest` and begins progress polling

### Requirement: Prompts page with HTMX
The prompts page SHALL list all configurable prompts with editable text areas. Saving and resetting SHALL use HTMX requests and update the relevant section.

#### Scenario: Edit and save a prompt
- **WHEN** the user edits the text area for a prompt and clicks Save
- **THEN** HTMX sends a PUT to `/prompts/{name}` with the new content, and a success message appears without full page reload

#### Scenario: Reset prompt to default
- **WHEN** the user clicks Reset on a prompt
- **THEN** HTMX sends a DELETE to `/prompts/{name}` and the text area updates to show the default content

### Requirement: Classless CSS framework
The frontend SHALL use a classless CSS framework (Pico CSS or similar) loaded from CDN. No CSS build pipeline SHALL be required.

#### Scenario: Styled without custom CSS classes
- **WHEN** the HTML templates use only semantic HTML elements (nav, main, section, article, table, form, button, input, textarea)
- **THEN** the page renders with clean, readable styling from the CSS framework without any custom class names
