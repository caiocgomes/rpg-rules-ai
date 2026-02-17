## MODIFIED Requirements

### Requirement: Batch ingestion of multiple files
The system SHALL accept a list of file paths and process them through the layered ingestion pipeline (parse → split → embed → store). Falha em um arquivo durante o parse SHALL NOT abortar o processamento dos demais. O resultado SHALL incluir status por arquivo (sucesso, skipped por duplicata, ou erro com mensagem) e progresso por fase.

#### Scenario: Multiple files ingested successfully
- **WHEN** a list of 5 markdown file paths is provided to the batch ingestion pipeline
- **THEN** all files are processed through the layered pipeline (parse all → split all → embed all → store all), and the result contains 5 entries with status "success"

#### Scenario: Partial failure in batch
- **WHEN** a batch of 3 files is submitted and the second file has a parsing error
- **THEN** the first and third files proceed through all pipeline phases, and the result for the second file contains status "error" with the exception message

#### Scenario: Batch with duplicate detection
- **WHEN** a batch contains a file whose book name is already indexed and replace is not enabled
- **THEN** that file is skipped with status "skipped" and the remaining files are processed normally through the layered pipeline

### Requirement: Progress callback during ingestion
The batch ingestion pipeline SHALL report progress by phase (parsing, splitting, embedding, storing) rather than by file. Each phase SHALL report items completed and total items.

#### Scenario: Progress updates during embedding phase
- **WHEN** a batch of files is being ingested and the embedding phase is active
- **THEN** progress reports SHALL include phase name "embedding", number of chunks embedded so far, and total chunks to embed
