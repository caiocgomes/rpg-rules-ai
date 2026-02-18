## Context

O app hoje é um monolito Streamlit em `app.py` que importa diretamente `caprag.graph`, `caprag.ingest`, `caprag.ingestion_job`, `caprag.prompts` e `caprag.config`. A lógica de negócio e a apresentação vivem no mesmo processo e no mesmo namespace. O `IngestionJob` guarda estado em `st.session_state`, que é por sessão de browser. Chamadas async passam por `asyncio.run()` dentro do Streamlit, criando event loops descartáveis.

Cobertura atual: 88% (67 testes), com gaps em `retriever.py`, `factory.py`, `multi_question.py` e `ingest.py:reindex_directory`.

Dois usuários: Caio (admin, edita prompts) e o GM da campanha (faz perguntas sobre regras).

## Goals / Non-Goals

**Goals:**
- Testes unitários cobrindo os módulos que ainda têm gaps, mockando apenas boundaries externos (OpenAI, Chroma)
- API FastAPI como única interface entre frontend e lógica de negócio
- Testes de integração contra a API usando TestClient
- Streamlit como cliente HTTP puro, sem imports de `caprag.*`
- FastAPI e Streamlit rodando no mesmo processo/container

**Non-Goals:**
- Autenticação na API (dois usuários confiáveis, rede local)
- Separar em microserviços ou containers distintos
- Websockets ou streaming de respostas (pode vir depois)
- Migrar de Streamlit para outro frontend

## Decisions

**1. FastAPI no mesmo processo, portas diferentes**

O `docker-compose` (ou o script de start) levanta uvicorn na porta 8000 e Streamlit na 8501. No Docker, ambos rodam no mesmo container via supervisor ou script shell simples. Em dev local, dois comandos (`uvicorn caprag.api:app` e `streamlit run app.py`).

Alternativa considerada: FastAPI embutido no Streamlit via thread. Descartado porque complica o event loop e mistura lifecycles.

**2. Endpoints da API mapeiam 1:1 com as operações do Streamlit**

```
POST   /ask                → graph.ainvoke (pergunta → resposta)
GET    /documents          → get_books_metadata()
POST   /documents/ingest   → inicia IngestionJob, retorna job_id
GET    /documents/jobs/{id} → get_progress() do job
DELETE /documents/{book}   → delete_book()
GET    /prompts            → lista prompts com conteúdo atual
GET    /prompts/{name}     → get_prompt_content()
PUT    /prompts/{name}     → save_prompt()
DELETE /prompts/{name}     → reset_prompt()
```

O estado de ingestão sai do `st.session_state` e vai para um dict in-memory no FastAPI, indexado por UUID. Mesma semântica de antes, mas server-side.

**3. Schemas de request/response com Pydantic**

Os modelos de response da API reutilizam os schemas existentes (`AnswerWithSources`, `ProgressUpdate`) quando possível. Novos models apenas para request bodies (`AskRequest`, `IngestRequest`) e wrappers de response onde necessário.

**4. Streamlit faz requests via httpx**

O `app.py` importa `httpx` e faz chamadas síncronas à API local. A URL base vem de uma env var `API_URL` com default `http://localhost:8000`. Zero imports de `caprag.*`.

**5. Fase 1: testes unitários antes do refactor**

Completar cobertura dos módulos com gaps antes de mexer na arquitetura:

- `retriever.py`: testar `get_vectorstore()` e `get_retriever()` mockando `OpenAIEmbeddings` e `Chroma`. Resetar os singletons (`_retriever = None`, `_vectorstore = None`) entre testes.
- `factory.py`: testar `get_strategy()` para ambas as estratégias patcheando `settings.retrieval_strategy`.
- `multi_question.py`: testar `execute()` mockando `ChatOpenAI`, `get_multi_question_prompt`, `get_retriever`. Verificar que main_question é appended, retriever chamado para cada question, contexto atribuído.
- `ingest.py:reindex_directory`: mockando `get_vectorstore`, `get_retriever`, `UnstructuredMarkdownLoader`.

Esses testes são a rede de segurança pro refactor. Se algo quebrar durante a separação, eles pegam.

**6. Fase 2: testes de integração contra a API**

Testes com `httpx.AsyncClient` + FastAPI `TestApp`. Mock apenas na OpenAI API (response fixture). Todo o resto roda real: prompts carregam do disco, grafo executa, retriever monta queries. Esses testes exercitam o pipeline inteiro e teriam pego os bugs de prompt que passaram pelos mocks unitários.

## Risks / Trade-offs

**Latência adicional do HTTP local entre Streamlit e FastAPI** → Negligível (localhost, payloads pequenos). A chamada real à OpenAI domina o tempo de resposta.

**Dois processos para gerenciar em dev** → Aceitável. Um Makefile ou script `run.sh` resolve. No Docker, supervisor ou entrypoint com `&`.

**IngestionJob em memória no FastAPI perde estado se o processo reiniciar** → Mesmo comportamento de antes (st.session_state também perdia). Aceitável para dois usuários.

**Singletons em `retriever.py` (`_retriever`, `_vectorstore`) complicam testes** → Resetar via monkeypatch entre testes. Não vale refatorar os singletons agora, só garantir que os testes limpam o estado.
