## ADDED Requirements

### Requirement: Multipart file upload endpoint
The API SHALL provide a `POST /documents/upload` endpoint that accepts one or more files via `multipart/form-data`. The endpoint SHALL save each file to the configured sources directory and return a `202 Accepted` response with a `job_id` for tracking the background ingestion.

#### Scenario: Upload single file
- **WHEN** a single markdown file is uploaded via multipart POST to `/documents/upload`
- **THEN** the file SHALL be saved to `{SOURCES_DIR}/{filename}`, a background ingestion job SHALL be started, and the response SHALL contain `{"job_id": "<uuid>"}` with HTTP status 202

#### Scenario: Upload multiple files
- **WHEN** 3 markdown files are uploaded in a single multipart POST to `/documents/upload`
- **THEN** all 3 files SHALL be saved to `{SOURCES_DIR}/`, a single ingestion job SHALL be created for all files, and the response SHALL contain one `job_id`

#### Scenario: Upload with replace flag
- **WHEN** files are uploaded with query parameter `replace=true`
- **THEN** existing books with matching filenames SHALL be deleted and re-ingested

#### Scenario: Upload non-markdown file
- **WHEN** a file with extension other than `.md` is uploaded
- **THEN** the API SHALL return HTTP 400 with error detail indicating only markdown files are accepted

### Requirement: File size within acceptable limits
The API SHALL accept markdown files up to 20MB. Files exceeding this limit SHALL be rejected with HTTP 413.

#### Scenario: File within size limit
- **WHEN** a 5MB markdown file is uploaded
- **THEN** the upload SHALL succeed and processing SHALL begin

#### Scenario: File exceeds size limit
- **WHEN** a 25MB file is uploaded
- **THEN** the API SHALL return HTTP 413 with error detail indicating the file is too large
