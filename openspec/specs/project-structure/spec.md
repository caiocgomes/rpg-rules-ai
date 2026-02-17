### Requirement: Python package structure with uv
The system SHALL be structured as a Python package (`caprag/`) with a `pyproject.toml` managed by `uv`. All dependencies previously installed via `!pip install` in the notebook MUST be declared in `pyproject.toml`.

#### Scenario: Install and run from clean environment
- **WHEN** a developer clones the repository and runs `uv sync`
- **THEN** all dependencies are installed and `streamlit run app.py` starts the application

### Requirement: Environment-based configuration
The system SHALL load all configuration (API keys, model names, Chroma persist directory) from environment variables, with support for `.env` files via pydantic-settings. No Colab-specific APIs (google.colab.userdata, drive.mount) SHALL remain in production code.

#### Scenario: Configuration via .env file
- **WHEN** a `.env` file exists with `OPENAI_API_KEY`, `CHROMA_PERSIST_DIR`, and other settings
- **THEN** the application loads these values at startup and uses them across all modules

#### Scenario: Missing required API key
- **WHEN** `OPENAI_API_KEY` is not set in environment or .env
- **THEN** the application fails at startup with a clear error message indicating the missing variable

### Requirement: Modular code organization
The notebook code SHALL be extracted into separate modules: `config.py` (settings), `ingest.py` (document ingestion), `retriever.py` (vector store and retriever setup), `graph.py` (LangGraph definition), `schemas.py` (Pydantic models), `prompts.py` (LangChain Hub references). `app.py` SHALL be the Streamlit entrypoint at the project root.

#### Scenario: Module independence
- **WHEN** `ingest.py` is imported
- **THEN** it does not trigger graph compilation or Streamlit initialization; each module is importable independently without side effects

### Requirement: Docker containerization
The system SHALL include a Dockerfile that builds a runnable image. Chroma data MUST be mountable as an external volume for persistence between container restarts.

#### Scenario: Build and run container
- **WHEN** a user runs `docker build` and `docker run` with a volume mount for the data directory
- **THEN** the Streamlit interface is accessible on the exposed port and the Chroma data persists across container restarts
