## Context

O CapaRAG hoje é um notebook Colab com ~30 cells que misturam setup de dependências, ingestão de documentos, definição de tipos, construção do grafo LangGraph e execução de queries. O vector store FAISS vive em memória e morre quando o runtime do Colab reinicia. Os documentos são markdowns no Google Drive, listados por glob hardcoded. Credenciais vêm do `google.colab.userdata`.

O grafo em si é simples e funcional: multi_question → retrieve → generate. A lógica agêntica (expansão de query, retrieval paralelo, resposta estruturada com citações) está correta e não precisa de refatoração conceitual, apenas de extração para módulos.

Os prompts (`cgomes/rag` e `gurps_multi_question`) são puxados do LangChain Hub em runtime. Isso é conveniente e pode ser mantido, evitando que prompts fiquem hardcoded no código.

## Goals / Non-Goals

**Goals:**

- Estrutura de projeto Python que rode fora do Colab, com `uv` e `pyproject.toml`
- Vector store persistente em disco, sobrevivendo a restarts
- Pipeline de ingestão separado: adicionar novos documentos sem reconstruir o índice inteiro
- Frontend Streamlit com chat e upload de documentos
- Configuração por variáveis de ambiente (`.env`), sem dependência de APIs do Colab
- Containerização básica para deploy

**Non-Goals:**

- Reescrever a lógica do grafo LangGraph (multi_question → retrieve → generate permanece)
- Autenticação de usuários no frontend (Streamlit roda como ferramenta interna por enquanto)
- Suporte a múltiplos vector stores simultâneos ou multi-tenancy
- API REST separada do Streamlit (o Streamlit é o ponto de acesso único por ora)
- Migração de prompts do LangChain Hub para local

## Decisions

### 1. Vector store: Chroma em vez de FAISS

O notebook já tentou Chroma (cell 13, falhou por falta do módulo). FAISS funciona bem para retrieval, mas persistência exige serialização manual (`faiss.write_index` / `faiss.read_index`) mais o `InMemoryStore` do docstore, que não persiste sozinho. Chroma resolve os dois problemas: persiste embeddings e metadados em disco nativamente, com `persist_directory`.

A alternativa seria manter FAISS com serialização manual. Funciona, mas obriga a gerenciar dois artefatos separados (índice FAISS + docstore pickled), e o `ParentDocumentRetriever` com FAISS + `InMemoryStore` não tem um caminho limpo de persistência do docstore. Chroma simplifica isso.

O `ParentDocumentRetriever` continua sendo usado, apenas com Chroma como backend em vez de FAISS. Os parâmetros de chunking (child: 200/40, parent: 2000/400) se mantêm.

### 2. Estrutura de módulos

```
caprag/
├── __init__.py
├── config.py          # Settings via pydantic-settings / .env
├── ingest.py          # Pipeline de ingestão: load markdown → chunk → embed → persist
├── retriever.py       # Construção do retriever (Chroma + ParentDocumentRetriever)
├── graph.py           # Definição do grafo LangGraph (State, nodes, compilação)
├── schemas.py         # Pydantic models (Citation, AnswerWithSources, Questions, etc.)
├── prompts.py         # Referências aos prompts do LangChain Hub
app.py                 # Streamlit entrypoint
```

A lógica de cada cell do notebook mapeia diretamente para um módulo. `graph.py` importa de `retriever.py` e `schemas.py`. `app.py` importa de `graph.py` e `ingest.py`. Sem camadas extras de abstração.

Alternativa considerada: separar em packages (`caprag/graph/`, `caprag/ingestion/`, etc.). Desnecessário neste estágio. O sistema tem três fluxos (ingestão, retrieval, interface) com pouca complexidade interna em cada um. Arquivos planos bastam; se algum módulo crescer, a separação acontece depois.

### 3. Ingestão incremental

O notebook hoje carrega todos os documentos de uma vez e reconstrói o vector store do zero. Para suportar upload de novos livros sem reindexar tudo, o pipeline de ingestão precisa:

1. Receber um arquivo markdown (via upload no Streamlit ou path local)
2. Extrair metadata (nome do livro a partir do filename)
3. Passar pelo mesmo pipeline de chunking (child/parent splitters)
4. Adicionar ao Chroma existente via `retriever.add_documents()`

Chroma lida com persistência automática. Não há necessidade de batch rebuild exceto em caso de mudança nos parâmetros de chunking ou embedding model (que exigiria reindexação completa).

### 4. Frontend Streamlit

Duas páginas (via `st.sidebar` ou tabs):

**Chat**: Input de texto, chamada ao grafo via `graph.ainvoke()`, exibição da resposta estruturada (answer, sources, citations, see_also). Histórico de conversa mantido via session_state + checkpointer do LangGraph.

**Upload**: File uploader para markdown, preview do arquivo, botão de indexação que dispara o pipeline de ingestão. Lista de documentos já indexados (extraída dos metadados do Chroma).

O Streamlit roda como entrypoint único (`streamlit run app.py`). Não há API REST intermediária; o Streamlit chama os módulos Python diretamente.

### 5. Configuração

Pydantic-settings com `.env` file. Variáveis:

- `OPENAI_API_KEY`
- `LANGSMITH_API_KEY` (opcional)
- `CHROMA_PERSIST_DIR` (default: `./data/chroma`)
- `LANGCHAIN_PROJECT` (default: `capa-rag`)
- `LLM_MODEL` (default: `gpt-4o-mini`)
- `EMBEDDING_MODEL` (default: `text-embedding-3-large`)

### 6. Containerização

Dockerfile simples: imagem base Python, `uv sync`, expose porta do Streamlit, `CMD streamlit run app.py`. Dados do Chroma montados como volume para persistência entre deploys.

Docker Compose opcional com volume nomeado para `./data/chroma`.

## Risks / Trade-offs

**Migração FAISS → Chroma pode alterar resultados de retrieval** → Os mesmos documentos com o mesmo embedding model produzem resultados muito similares, mas não idênticos (Chroma usa HNSW, FAISS usava L2 bruto). Aceitar a diferença; o ganho em persistência compensa. Se a qualidade cair perceptivelmente, ajustar `n_results` ou testar com `collection_metadata={"hnsw:space": "l2"}`.

**Prompts no LangChain Hub criam dependência externa** → Se o Hub ficar fora do ar, o sistema quebra. Risco baixo, mas existe. Mitigação futura: cache local dos prompts. Não é escopo desta mudança.

**Streamlit não escala para muitos usuários simultâneos** → Cada sessão Streamlit mantém estado em memória. Para uso interno com poucos usuários, não é problema. Se virar público, precisaria de uma API separada. Não é escopo agora.

**Reindexação completa necessária se mudar embedding model ou chunk sizes** → Não há como migrar incrementalmente. O pipeline de ingestão precisaria de um comando "reindex all" para esses casos. Incluir como task, mas não como capability separada.
