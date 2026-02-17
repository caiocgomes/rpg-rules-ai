## ADDED Requirements

### Requirement: Centralized graph singleton
The `caprag/services.py` module SHALL maintain a single lazily-initialized graph instance. All graph invocations across the application MUST go through `services.ask_question()`. No other module SHALL instantiate or cache the graph.

#### Scenario: First question initializes graph
- **WHEN** `ask_question()` is called for the first time in the process
- **THEN** the graph is built once via `build_graph()` and cached in the module-level singleton

#### Scenario: Subsequent questions reuse graph
- **WHEN** `ask_question()` is called after the graph has been initialized
- **THEN** the same graph instance is reused without calling `build_graph()` again

### Requirement: Centralized job registry
The `caprag/services.py` module SHALL maintain a single job registry (`dict[str, IngestionJob]`). All job creation and progress queries MUST go through `services.create_ingestion_job()` and `services.get_job_progress()`.

#### Scenario: Job created via API is visible to frontend
- **WHEN** an ingestion job is created through the JSON API endpoint
- **THEN** the same job is retrievable by its ID through the HTMX progress polling endpoint

#### Scenario: Job created via HTMX is visible to API
- **WHEN** an ingestion job is created through the HTMX upload endpoint
- **THEN** the same job progress is retrievable through `GET /api/documents/jobs/{job_id}`

### Requirement: Domain validation in service layer
The service layer SHALL validate domain rules and raise standard Python exceptions. Routers SHALL catch these exceptions and translate to their respective response formats.

#### Scenario: Invalid file extension
- **WHEN** `validate_upload_files()` receives a path that does not end in `.md`
- **THEN** a `ValueError` is raised with a message identifying the invalid filename

#### Scenario: Non-existent path for ingestion
- **WHEN** `create_ingestion_job()` receives a path that does not exist on disk
- **THEN** a `FileNotFoundError` is raised with a message identifying the missing path

#### Scenario: Unknown prompt name
- **WHEN** `get_prompt()` or `save_prompt()` is called with a name not in `PROMPT_CONFIGS`
- **THEN** a `KeyError` is raised with a message identifying the unknown prompt name

### Requirement: Service functions accept plain Python types
Service functions SHALL accept and return plain Python types (`str`, `Path`, `dict`, `list`), never FastAPI-specific types (`UploadFile`, `Request`, `HTTPException`).

#### Scenario: ask_question interface
- **WHEN** `ask_question(question: str)` is called
- **THEN** it returns the structured answer dict from the graph, without any HTTP-layer wrapping

#### Scenario: create_ingestion_job interface
- **WHEN** `create_ingestion_job(paths: list[Path], replace: bool)` is called
- **THEN** it returns the `job_id` string and starts the background ingestion
