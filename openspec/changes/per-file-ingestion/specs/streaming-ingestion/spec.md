## ADDED Requirements

### Requirement: Per-file pipeline processing
The ingestion pipeline SHALL process each file through the complete pipeline (parse → split → contextualize → entity extract → embed → store) before moving to the next file. All intermediate data structures for a file SHALL be released before processing the next file.

#### Scenario: Memory bounded by single file
- **WHEN** 10 files are submitted for ingestion
- **THEN** peak memory usage is proportional to the largest single file, not to the sum of all files

#### Scenario: Previous files persisted before next starts
- **WHEN** file 3 of 5 is being processed
- **THEN** files 1 and 2 are already fully stored in Chroma and docstore

### Requirement: Streaming embed and store
The pipeline SHALL embed child chunks in batches of `EMBED_BATCH_SIZE` and store each batch in Chroma immediately after embedding. The embedding vectors for a batch SHALL be discarded before the next batch is embedded. The pipeline SHALL NOT accumulate all embeddings in memory.

#### Scenario: Batch embed-store cycle
- **WHEN** a file produces 1000 child chunks and EMBED_BATCH_SIZE is 500
- **THEN** the pipeline embeds chunks 0-499, stores them, discards the vectors, then embeds chunks 500-999 and stores them

#### Scenario: Parent documents stored after all children
- **WHEN** all child chunks for a file have been embedded and stored
- **THEN** the parent documents for that file are serialized and stored in the docstore

### Requirement: Immediate entity storage per file
When entity extraction is enabled, the pipeline SHALL extract entities from parent chunks of the current file and store them in the entity index before processing the next file. Entity results SHALL NOT be accumulated across files.

#### Scenario: Entities stored per file
- **WHEN** entity extraction is enabled and file A is fully processed
- **THEN** entities from file A are already in the SQLite entity index before file B begins processing
