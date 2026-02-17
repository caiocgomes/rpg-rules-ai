## 1. Service Layer

- [x] 1.1 Create `caprag/services.py` with module-level `_graph` and `_jobs` singletons, lazy `_get_graph()` internal function
- [x] 1.2 Implement `ask_question(question: str) -> dict` que invoca o graph e retorna `result["answer"]`
- [x] 1.3 Implement `create_ingestion_job(paths: list[Path], replace: bool) -> str` que valida paths, cria `IngestionJob`, registra em `_jobs`, chama `start()`, retorna `job_id`
- [x] 1.4 Implement `get_job_progress(job_id: str) -> dict` que busca em `_jobs` e levanta `KeyError` se não encontrar
- [x] 1.5 Implement `list_books() -> list[dict]` delegando para `ingest.get_books_metadata()`
- [x] 1.6 Implement `delete_book(book: str)` delegando para `ingest.delete_book()`
- [x] 1.7 Implement funções de prompt: `list_prompts()`, `get_prompt(name)`, `save_prompt(name, content)`, `reset_prompt(name)` com validação de `name in PROMPT_CONFIGS` levantando `KeyError`
- [x] 1.8 Implement `validate_upload_paths(paths: list[Path])` que levanta `ValueError` para extensões não-.md

## 2. Migrar api.py

- [x] 2.1 Remover singletons `_graph`, `_jobs`, `_get_graph()` de `api.py`
- [x] 2.2 Remover imports diretos de `graph`, `ingest`, `ingestion_job`, `prompts` de `api.py`
- [x] 2.3 Fazer `POST /api/ask` delegar para `services.ask_question()`
- [x] 2.4 Fazer endpoints de documents (`GET /api/documents`, `POST /api/documents/upload`, `POST /api/documents/ingest`, `GET /api/documents/jobs/{job_id}`, `DELETE /api/documents/{book}`) delegarem para services, traduzindo exceções em `HTTPException`
- [x] 2.5 Fazer endpoints de prompts (`GET /api/prompts`, `GET /api/prompts/{name}`, `PUT /api/prompts/{name}`, `DELETE /api/prompts/{name}`) delegarem para services, traduzindo `KeyError` em `HTTPException(404)`

## 3. Migrar frontend.py

- [x] 3.1 Remover singletons `_graph`, `_jobs`, `_get_graph()` de `frontend.py`
- [x] 3.2 Remover imports diretos de `graph`, `ingest`, `ingestion_job`, `prompts` de `frontend.py`
- [x] 3.3 Fazer `POST /chat/ask` delegar para `services.ask_question()`
- [x] 3.4 Fazer endpoints HTMX de documents delegarem para services, traduzindo exceções em `HTMLResponse` com mensagem de erro
- [x] 3.5 Fazer endpoints HTMX de prompts delegarem para services, traduzindo `KeyError` em `HTMLResponse(404)`

## 4. Verificação

- [x] 4.1 Rodar testes existentes (`uv run pytest tests/ -v`) e garantir que todos passam
- [x] 4.2 Verificar que nenhum módulo além de `services.py` importa `build_graph`, `IngestionJob` diretamente ou mantém singletons de `_graph`/`_jobs`
