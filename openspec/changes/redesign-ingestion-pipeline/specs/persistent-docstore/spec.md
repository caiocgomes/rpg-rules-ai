## ADDED Requirements

### Requirement: Persistent parent chunk storage
The system SHALL use a persistent, filesystem-backed store (`LocalFileStore`) for parent chunks instead of `InMemoryStore`. Parent chunks SHALL survive server restarts without requiring re-ingestion.

#### Scenario: Parent chunks persist across restart
- **WHEN** documents are ingested, the server is restarted, and a search query is executed
- **THEN** the `ParentDocumentRetriever` SHALL retrieve parent chunks from the persistent docstore and return complete results

#### Scenario: Docstore directory auto-created
- **WHEN** the server starts and the docstore directory does not exist
- **THEN** the system SHALL create the directory at the configured path (default `./data/docstore/`)

### Requirement: Docstore consistency with vectorstore
Parent chunk IDs stored in the docstore SHALL match the `doc_id` metadata field in child chunks stored in the vectorstore. The ingestion pipeline SHALL guarantee this consistency.

#### Scenario: ID mapping is correct after ingestion
- **WHEN** a document is ingested and a child chunk is retrieved from the vectorstore
- **THEN** the child chunk's `doc_id` metadata SHALL correspond to a valid parent chunk key in the docstore

#### Scenario: Delete removes from both stores
- **WHEN** `delete_book("Book.md")` is called
- **THEN** child chunks SHALL be removed from the vectorstore AND their corresponding parent chunks SHALL be removed from the docstore
