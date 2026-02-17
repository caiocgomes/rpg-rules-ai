import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str
    langsmith_api_key: str = ""
    langchain_project: str = "capa-rag"
    chroma_persist_dir: str = "./data/chroma"
    sources_dir: str = "./data/sources"
    docstore_dir: str = "./data/docstore"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-large"
    retrieval_strategy: Literal["multi-hop", "multi-question"] = "multi-hop"
    retriever_k: int = 12
    retriever_fetch_k: int = 30
    retriever_lambda_mult: float = 0.7


settings = Settings()
os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

Path(settings.sources_dir).mkdir(parents=True, exist_ok=True)
Path(settings.docstore_dir).mkdir(parents=True, exist_ok=True)
