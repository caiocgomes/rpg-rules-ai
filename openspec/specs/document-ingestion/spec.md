## MODIFIED Requirements

### Requirement: Incremental ingestion without full reindex
The system SHALL add new documents to the existing Chroma collection without rebuilding the entire index. Documents already indexed SHALL NOT be re-embedded. When `replace=True` is passed, the system SHALL delete existing chunks for that book and re-ingest, instead of skipping.

#### Scenario: Add document to existing collection
- **WHEN** a new markdown file is ingested and the Chroma collection already contains previously indexed documents
- **THEN** only the new document's chunks are embedded and added; existing documents remain unchanged

#### Scenario: Duplicate document handling (default)
- **WHEN** a document with the same filename as an already-indexed document is ingested with `replace=False` (default)
- **THEN** the system SHALL warn the user and skip ingestion (not create duplicate entries)

#### Scenario: Duplicate document handling (replace mode)
- **WHEN** a document with the same filename as an already-indexed document is ingested with `replace=True`
- **THEN** the system SHALL delete all existing chunks for that book and re-ingest the new file
