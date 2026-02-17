## ADDED Requirements

### Requirement: Ingest markdown documents into vector store
The system SHALL accept markdown files (.md) and process them through the chunking pipeline (child splitter: 200 chars / 40 overlap, parent splitter: 2000 chars / 400 overlap), generate embeddings, and persist the results in the Chroma vector store. O nome do livro SHALL ser extraído do filename e armazenado como metadata `book` em cada documento.

#### Scenario: Single markdown file ingestion
- **WHEN** a markdown file is provided to the ingestion pipeline
- **THEN** the system chunks the document using ParentDocumentRetriever, generates embeddings via text-embedding-3-large, persists to Chroma, and the document becomes retrievable by the RAG graph

#### Scenario: Metadata extraction from filename
- **WHEN** a file named "GURPS 4e - Martial Arts.md" is ingested
- **THEN** the metadata field `book` SHALL contain "GURPS 4e - Martial Arts.md"

### Requirement: Incremental ingestion without full reindex
The system SHALL add new documents to the existing Chroma collection without rebuilding the entire index. Documents already indexed SHALL NOT be re-embedded.

#### Scenario: Add document to existing collection
- **WHEN** a new markdown file is ingested and the Chroma collection already contains previously indexed documents
- **THEN** only the new document's chunks are embedded and added; existing documents remain unchanged

#### Scenario: Duplicate document handling
- **WHEN** a document with the same filename as an already-indexed document is ingested
- **THEN** the system SHALL warn the user and skip ingestion (not create duplicate entries)

### Requirement: Full reindex capability
The system SHALL provide a way to rebuild the entire vector store from scratch (clearing existing data and re-ingesting all documents). This is necessary when embedding model or chunk parameters change.

#### Scenario: Reindex triggered
- **WHEN** the user triggers a full reindex
- **THEN** the existing Chroma collection is cleared and all source documents are re-ingested with current parameters
