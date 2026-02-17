## ADDED Requirements

### Requirement: Layered ingestion pipeline
The system SHALL process ingestion in four sequential phases over the entire batch of files: parse, split, embed, store. Each phase SHALL complete for all files before the next phase begins.

#### Scenario: Full pipeline execution
- **WHEN** 3 markdown files are submitted for ingestion
- **THEN** Phase 1 (parse) SHALL load all 3 files into documents, Phase 2 (split) SHALL split all documents into parent and child chunks, Phase 3 (embed) SHALL generate embeddings for all child chunks, and Phase 4 (store) SHALL persist all chunks to vectorstore and docstore

#### Scenario: Batch embedding reduces API calls
- **WHEN** 5 files producing 2000 total child chunks are ingested
- **THEN** the embedding phase SHALL call the embedding API in sub-batches (max 500 chunks per call) rather than per-file, resulting in 4 API calls instead of 5+ per-file calls

### Requirement: Sub-batch storage for fault tolerance
Phase 4 (store) SHALL persist embeddings and parent chunks in sub-batches of configurable size. If a sub-batch fails, previously stored sub-batches SHALL remain intact.

#### Scenario: Partial storage failure
- **WHEN** 1000 child chunks are being stored in sub-batches of 100 and the 6th sub-batch fails
- **THEN** the first 500 chunks SHALL remain in the vectorstore, and the job SHALL report an error indicating which sub-batch failed

### Requirement: Phase-level progress reporting
The ingestion job SHALL report progress per phase, including: current phase name, items completed in current phase, total items in current phase.

#### Scenario: Progress during embedding phase
- **WHEN** the embedding phase is processing 2000 child chunks and 500 have been embedded
- **THEN** the progress endpoint SHALL return `{"phase": "embedding", "phase_completed": 500, "phase_total": 2000, "status": "running"}`

#### Scenario: Progress at phase transition
- **WHEN** the parse phase completes and the split phase begins
- **THEN** the progress endpoint SHALL reflect the new phase with reset phase_completed counter

### Requirement: Parse phase error isolation
If a file fails to parse in Phase 1, the system SHALL skip that file, record the error, and continue parsing remaining files. Successfully parsed files SHALL proceed through subsequent phases.

#### Scenario: One file fails to parse
- **WHEN** 5 files are submitted and the 3rd file has invalid content
- **THEN** 4 files SHALL proceed through split/embed/store phases, and the job results SHALL include an error entry for the 3rd file
