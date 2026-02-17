# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is CapaRAG

Agentic RAG system for answering questions about RPG in general (rules, mechanics, lore, systems). Supports English and Portuguese queries. Currently indexed against GURPS 4e rulebooks, but the architecture is system-agnostic.

## Architecture Principle

Backend and frontend MUST be decoupled. The JSON API (`/api/` prefix in `caprag/api.py`) is the contract between them. The current Jinja2+HTMX frontend is one consumer of that API, but the backend should never assume a specific frontend. Any new feature must expose a JSON API endpoint first; frontend routes in `caprag/frontend.py` consume those endpoints or replicate the logic via shared modules.

## Backend Architecture

LangGraph state machine with two nodes:

1. **retrieve** - Delegates to a pluggable `RetrievalStrategy` that populates the state with relevant documents
2. **generate** - Synthesizes structured answer with citations, sources, and "see also" suggestions

The retrieval strategy is selected via `RETRIEVAL_STRATEGY` env var (default: `multi-hop`):

- **MultiHopStrategy** - Iterative retrieval: expands the query, retrieves, then uses an LLM to analyze if context is sufficient or if additional searches are needed. Loops up to 3 hops. Handles cross-book rule interactions.
- **MultiQuestionStrategy** - Single-pass: expands the query into sub-questions and retrieves all in parallel. Faster but misses cross-references.

Both strategies implement `RetrievalStrategy` ABC from `caprag/strategies/base.py`. New strategies can be added by subclassing and registering in the factory (`caprag/strategies/factory.py`).

State flows through a `State` class extending `MessagesState` with typed fields: `main_question`, `questions` (expanded queries with context), and `answer` (structured response with citations). Defined in `caprag/schemas.py`.

### Storage Layer

Retrieval uses hierarchical chunking: child chunks (200 chars) for retrieval precision, parent chunks (2000 chars) for context completeness. The retriever uses MMR (Maximal Marginal Relevance) with `k=12`, `fetch_k=30`, `lambda_mult=0.7` to balance relevance and diversity across source books. These are configurable via `RETRIEVER_K`, `RETRIEVER_FETCH_K`, `RETRIEVER_LAMBDA_MULT` env vars.

- **Vector store**: Chroma with persistent storage in `./data/chroma`. `BatchedChroma` subclass auto-splits writes into batches of 100 to avoid SQLite variable limits.
- **Docstore**: `LocalFileStore` at `./data/docstore/` stores parent documents. Passed as `byte_store=` to `ParentDocumentRetriever` (NOT `docstore=`), which wraps it with `create_kv_docstore` for automatic `Document` serialization/deserialization via langchain `dumps`/`loads`.
- **Sources**: uploaded markdown files saved to `./data/sources/`.

Parent documents are serialized with `langchain_core.load.dumps()` in `pipeline.py`. This preserves the full `Document` including metadata (book name, start_index). Changing the serialization format requires a full reindex.

## Frontend

Jinja2 templates + HTMX served directly by FastAPI. No separate frontend process. Templates live in `caprag/templates/` (with fragments in `caprag/templates/fragments/`), static assets in `caprag/static/`. CSS is Pico CSS (CDN) with minimal overrides in `style.css`. HTMX loaded locally from `caprag/static/htmx.min.js`.

Frontend routes are in `caprag/frontend.py` (APIRouter mounted at root). JSON API routes live under `/api/` prefix in `caprag/api.py`. Three pages: Chat (`/`), Documents (`/documents`), Prompts (`/prompts/page`). HTMX handles all async interactions (chat submission, upload progress polling, document delete, prompt save/reset).

## Running

Single process: FastAPI serves both the API and frontend on port 8100.

Local development:

```bash
uv sync
cp .env.example .env   # fill in OPENAI_API_KEY
./dev.sh
```

Or via Docker:

```bash
docker compose up --build
```

## Testing

```bash
OPENAI_API_KEY=test-key uv run pytest tests/ -v
```

Single test:
```bash
OPENAI_API_KEY=test-key uv run pytest tests/test_strategies.py::test_multi_hop_single_hop_sufficient -v
```

Tests require `OPENAI_API_KEY` env var set (any value works for unit tests since LLM calls are mocked). Tests cover strategy interface, config validation, document deduplication, and multi-hop loop behavior.

## Configuration

All settings via `.env` file (see `.env.example`). Required: `OPENAI_API_KEY`. Optional: `LANGSMITH_API_KEY`, `CHROMA_PERSIST_DIR`, `DOCSTORE_DIR`, `SOURCES_DIR`, `LLM_MODEL`, `EMBEDDING_MODEL`, `RETRIEVAL_STRATEGY` (`multi-hop` or `multi-question`).

The `config.py` module exports `OPENAI_API_KEY` to the environment on import so that LangChain components (which read from env, not from settings) can find it. It also auto-creates `data/` subdirectories on startup.

## Key Dependencies

LangGraph (orchestration), langchain-classic (ParentDocumentRetriever, LocalFileStore), langchain-openai (LLM/embeddings with text-embedding-3-large), Chroma (vector store with persistence), Jinja2 + HTMX (frontend), pydantic-settings (configuration), unstructured[md] + nltk (document parsing). Managed via `uv` and `pyproject.toml`.

## Document Ingestion

Two upload paths: multipart upload via `POST /api/documents/upload` (20MB limit, .md only), or path-based ingest via `POST /api/documents/ingest`. Both create an `IngestionJob` that runs asynchronously and returns a `job_id` for progress polling via `GET /api/documents/jobs/{job_id}`.

Ingestion uses a layered pipeline (`caprag/pipeline.py`): parse all files, split into parent/child chunks, embed in batches of 500, store in Chroma + docstore. Each phase reports progress separately. The pipeline handles errors per-file (one failure doesn't block others) and supports `replace` mode to delete existing book chunks before re-ingesting.

`caprag/ingest.py` provides `delete_book()` (removes from both vectorstore and docstore), `get_books_metadata()`, `get_indexed_books()`, and `reindex_directory()`. Full reindex clears the collection and re-runs the pipeline.

## Prompts

Two editable prompts: `rag` (answer generation) and `multi_question` (query expansion). Defaults are bundled; custom overrides saved to `data/prompts/`. Managed via API (`GET/PUT/DELETE /api/prompts/{name}`) and the Prompts page in the frontend.

## OpenSpec

Project uses OpenSpec (`openspec/` directory) for artifact-driven development. Commands available via `/opsx:*` skills (new, explore, continue, apply, verify, archive, ff, sync, onboard, bulk-archive). Config at `openspec/config.yaml` uses `spec-driven` schema.

## Observability

LangSmith project name: `capa-rag`. Tracing enabled when `LANGSMITH_API_KEY` is set.
