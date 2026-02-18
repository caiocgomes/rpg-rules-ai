## Why

O Streamlit importa diretamente módulos do `caprag` (graph, ingest, retriever, prompts, config), instancia objetos, gerencia threads e chama `asyncio.run()` inline. Não existe camada intermediária. Isso cria dois problemas concretos: primeiro, qualquer mudança num módulo backend que passe nos testes unitários mockados pode quebrar silenciosamente em produção (já aconteceu duas vezes com mudanças em prompts). Segundo, o frontend é o backend, o que impede testes de integração reais e torna impossível trocar ou complementar a interface sem reescrever tudo.

A separação introduz uma API FastAPI como única interface entre o Streamlit e a lógica de negócio. O Streamlit passa a ser um cliente HTTP puro, e a API vira a superfície testável do sistema.

## What Changes

- **Fase 1: Rede de segurança.** Testes unitários nos módulos que ainda não têm cobertura adequada (`retriever.py`, `factory.py`, `multi_question.py`, `ingest.py:reindex_directory`). Mock apenas no boundary externo (OpenAI API, Chroma client). Esses testes protegem contra regressão durante o refactor.
- **Fase 2: API FastAPI.** Novo módulo `caprag/api.py` expondo endpoints REST que encapsulam toda a lógica existente. Endpoints: `POST /ask`, `GET /documents`, `POST /documents/ingest`, `DELETE /documents/{book}`, `GET /prompts`, `PUT /prompts/{name}`, `DELETE /prompts/{name}`. FastAPI roda no mesmo processo que o Streamlit (mesma instância, portas diferentes).
- **Fase 2: Testes de integração.** Testes usando FastAPI TestClient que exercitam o pipeline real (grafo, prompts, retriever) com mock apenas na OpenAI API. Esses testes teriam pego os bugs de prompt que passaram despercebidos.
- **BREAKING**: `app.py` reescrito. Deixa de importar qualquer módulo de `caprag` exceto talvez config. Todas as operações passam pela API via `requests`/`httpx`.

## Capabilities

### New Capabilities
- `api`: API REST FastAPI encapsulando toda a lógica de negócio (ask, documents, prompts)

### Modified Capabilities
- `web-interface`: Streamlit passa a ser cliente HTTP da API, sem imports diretos do backend

## Impact

- `caprag/api.py`: módulo novo, ponto de entrada único para toda operação de backend
- `app.py`: rewrite completo, vira cliente HTTP puro
- `tests/`: novos testes unitários (fase 1) e testes de integração contra a API (fase 2)
- `docker-compose.yml`: possível ajuste de portas (FastAPI + Streamlit no mesmo container)
- Dependência nova: `fastapi`, `uvicorn`, `httpx` (para TestClient e para o Streamlit chamar a API)
