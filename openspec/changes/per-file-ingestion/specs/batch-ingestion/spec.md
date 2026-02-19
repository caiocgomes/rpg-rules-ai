## MODIFIED Requirements

### Requirement: Progress callback during ingestion
The batch ingestion pipeline SHALL accept an optional progress callback that is invoked after each file completes. The callback SHALL receive a progress dict with: phase set to "ingesting", phase_completed as the number of files processed so far, phase_total as the total number of files, file_results as a list of per-file outcomes, and status as "running", "done", or "error".

#### Scenario: Progress updates during batch
- **WHEN** a batch of 3 files is ingested with a progress callback registered
- **THEN** the callback is invoked at least 3 times with phase_completed incrementing from 1 to 3, and file_results growing with each completed file

#### Scenario: Progress on file skip
- **WHEN** a file is skipped because it is already indexed
- **THEN** the callback is invoked with the file recorded as "skipped" in file_results and phase_completed incremented
