## 1. Rede de segurança: testes unitários

- [x] 1.1 Testes para `retriever.py`: `get_vectorstore()` e `get_retriever()` mockando `OpenAIEmbeddings` e `Chroma`. Resetar singletons entre testes.
- [x] 1.2 Testes para `factory.py`: `get_strategy()` retorna `MultiHopStrategy` e `MultiQuestionStrategy` conforme config.
- [x] 1.3 Testes para `multi_question.py`: `execute()` completo mockando ChatOpenAI, prompt e retriever. Verificar append de main_question, chamadas ao retriever, atribuição de contexto.
- [x] 1.4 Testes para `ingest.py:reindex_directory`: mockando vectorstore, retriever, loader. Cobrir linhas 162-180.
- [x] 1.5 Rodar cobertura e confirmar que todos os módulos estão acima de 85%.

## 2. Setup FastAPI

- [x] 2.1 Adicionar dependências: `fastapi`, `uvicorn`, `httpx`.
- [x] 2.2 Criar `caprag/api.py` com app FastAPI, healthcheck `GET /health`.
- [x] 2.3 Criar script de start que levanta uvicorn e streamlit (dev e Docker).

## 3. Endpoints da API

- [x] 3.1 `POST /ask`: recebe `{"question": str}`, executa grafo, retorna `AnswerWithSources`.
- [x] 3.2 `GET /documents`: retorna lista de livros com metadata.
- [x] 3.3 `POST /documents/ingest`: recebe paths, inicia IngestionJob, retorna job_id.
- [x] 3.4 `GET /documents/jobs/{job_id}`: retorna progresso do job.
- [x] 3.5 `DELETE /documents/{book}`: remove livro do vector store.
- [x] 3.6 `GET /prompts`: lista todos os prompts com conteúdo, variáveis e flag is_custom.
- [x] 3.7 `GET /prompts/{name}`: retorna conteúdo do prompt.
- [x] 3.8 `PUT /prompts/{name}`: salva prompt editado.
- [x] 3.9 `DELETE /prompts/{name}`: reset ao default.

## 4. Testes de integração contra a API

- [x] 4.1 Teste `POST /ask` com mock apenas na OpenAI API, pipeline real.
- [x] 4.2 Testes dos endpoints de documents (list, ingest, progress, delete).
- [x] 4.3 Testes dos endpoints de prompts (list, get, put, delete).

## 5. Rewrite do Streamlit

- [x] 5.1 Reescrever aba Chat: `POST /ask` via httpx.
- [x] 5.2 Reescrever aba Documents: `GET/POST/DELETE /documents` via httpx, polling de progress.
- [x] 5.3 Reescrever aba Prompts: `GET/PUT/DELETE /prompts` via httpx.
- [x] 5.4 Remover todos os imports de `caprag.*` do `app.py`.
- [x] 5.5 Adicionar config `API_URL` com default `http://localhost:8000`.

## 6. Infra

- [x] 6.1 Atualizar `Dockerfile` e `docker-compose.yml` para rodar FastAPI + Streamlit.
- [x] 6.2 Rodar suite completa de testes (unitários + integração) e confirmar verde.
