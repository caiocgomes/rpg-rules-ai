#!/bin/bash
# Start FastAPI for local development (serves both API and frontend)

uv run uvicorn caprag.api:app --host 0.0.0.0 --port 8100 --reload
