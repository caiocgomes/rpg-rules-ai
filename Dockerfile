FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen

COPY rpg_rules_ai/ rpg_rules_ai/

EXPOSE 8100

CMD ["uv", "run", "uvicorn", "rpg_rules_ai.api:app", "--host", "0.0.0.0", "--port", "8100"]
