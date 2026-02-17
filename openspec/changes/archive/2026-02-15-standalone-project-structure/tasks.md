## 1. Project Scaffolding

- [x] 1.1 Criar `pyproject.toml` com todas as dependências (langchain-openai, langgraph, chromadb, langchain-community, langchain-text-splitters, unstructured[md], nltk, pydantic-settings, streamlit, langgraph-checkpoint-sqlite) e metadata do projeto. Configurar para uso com `uv`.
- [x] 1.2 Criar estrutura de diretórios: `caprag/` com `__init__.py`, `app.py` na raiz, `data/` no .gitignore
- [x] 1.3 Criar `.env.example` com todas as variáveis documentadas (OPENAI_API_KEY, LANGSMITH_API_KEY, CHROMA_PERSIST_DIR, LANGCHAIN_PROJECT, LLM_MODEL, EMBEDDING_MODEL)
- [x] 1.4 Adicionar `.gitignore` com `.env`, `data/`, `__pycache__/`, `*.egg-info/`

## 2. Configuration

- [x] 2.1 Criar `caprag/config.py` com classe Settings usando pydantic-settings, carregando do `.env`. Incluir defaults para CHROMA_PERSIST_DIR (`./data/chroma`), LLM_MODEL (`gpt-4o-mini`), EMBEDDING_MODEL (`text-embedding-3-large`), LANGCHAIN_PROJECT (`capa-rag`). Falhar com erro claro se OPENAI_API_KEY não estiver definida.

## 3. Schemas e Prompts

- [x] 3.1 Criar `caprag/schemas.py` extraindo Citation, AnswerWithSources, Question, Questions e State do notebook
- [x] 3.2 Criar `caprag/prompts.py` com funções que puxam prompts do LangChain Hub (`cgomes/rag`, `gurps_multi_question`)

## 4. Retriever

- [x] 4.1 Criar `caprag/retriever.py` com função que instancia Chroma (com `persist_directory` do config), configura child/parent splitters, e retorna um ParentDocumentRetriever. O retriever deve carregar a collection existente se o diretório já contiver dados.

## 5. Document Ingestion

- [x] 5.1 Criar `caprag/ingest.py` com função que recebe path de um arquivo markdown, carrega via UnstructuredMarkdownLoader, extrai metadata `book` do filename, e adiciona ao retriever existente via `retriever.add_documents()`
- [x] 5.2 Implementar detecção de duplicata: checar se já existe documento com mesmo `book` na collection Chroma antes de ingerir. Emitir warning e pular se já existe.
- [x] 5.3 Implementar função de reindex completo: limpar collection Chroma e re-ingerir todos os documentos de um diretório fornecido

## 6. LangGraph

- [x] 6.1 Criar `caprag/graph.py` extraindo os nodes (multi_question, retrieve, generate), a construção do StateGraph, e a compilação com MemorySaver checkpointer. Importar schemas de `schemas.py`, retriever de `retriever.py`, prompts de `prompts.py`.

## 7. Streamlit Interface

- [x] 7.1 Criar `app.py` com página de Chat: input de texto, invocação do grafo via `graph.ainvoke()`, exibição formatada da resposta (answer, sources, citations com quote+source, see_also). Manter histórico de conversa via st.session_state + thread_id do checkpointer.
- [x] 7.2 Adicionar página de Upload/Documentos: file_uploader restrito a .md, botão de ingestão que chama pipeline de `ingest.py`, mensagem de confirmação com contagem de chunks. Listar documentos indexados extraindo valores distintos de metadata `book` do Chroma.

## 8. Docker

- [x] 8.1 Criar `Dockerfile` com imagem base Python, instalação via `uv sync`, expose da porta Streamlit, CMD `streamlit run app.py`
- [x] 8.2 Criar `docker-compose.yml` com volume nomeado para `./data/chroma`

## 9. Cleanup e Documentação

- [x] 9.1 Atualizar `CLAUDE.md` para refletir a nova estrutura de projeto, comandos de build/run, e arquitetura modular
