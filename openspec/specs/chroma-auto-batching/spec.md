## ADDED Requirements

### Requirement: Auto-batched vectorstore writes
The vectorstore SHALL automatically split write operations into sub-batches that respect the Chroma/SQLite `max_batch_size` limit. This SHALL apply to all write paths (add_texts, add_documents) transparently, without requiring callers to manage batch sizes.

#### Scenario: Write within limit
- **WHEN** `add_texts` is called with N texts where N <= `max_batch_size`
- **THEN** the operation SHALL complete in a single batch with no splitting

#### Scenario: Write exceeding limit
- **WHEN** `add_texts` is called with N texts where N > `max_batch_size`
- **THEN** the operation SHALL split into ceil(N / max_batch_size) sub-batches, each processed sequentially, and return all generated IDs concatenated in order

#### Scenario: ParentDocumentRetriever expansion exceeds limit
- **WHEN** `ParentDocumentRetriever.add_documents` is called with documents that expand to more than `max_batch_size` child chunks
- **THEN** the underlying vectorstore SHALL handle the overflow transparently without raising a batch size error

### Requirement: Dynamic batch size detection
The vectorstore SHALL query the actual `max_batch_size` from the Chroma client at runtime instead of using a hardcoded value. This ensures correct behavior across different SQLite compilations and Chroma versions.

#### Scenario: Standard SQLite compilation
- **WHEN** the system runs on SQLite with MAX_VARIABLE_NUMBER=32767
- **THEN** `max_batch_size` SHALL be 5461 (32767 / 6)

#### Scenario: Non-standard SQLite compilation
- **WHEN** the system runs on a SQLite build with a different MAX_VARIABLE_NUMBER
- **THEN** `max_batch_size` SHALL reflect the actual compiled limit, not a hardcoded value
