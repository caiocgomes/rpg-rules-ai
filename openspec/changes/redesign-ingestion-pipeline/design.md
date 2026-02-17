## Context

O CapaRAG ingere livros de RPG em formato markdown, processa em hierarchical chunks (parent 2000 chars, child 200 chars), gera embeddings via OpenAI e armazena no Chroma. Hoje o pipeline opera por arquivo: para cada .md, faz parse → split → embed → store sequencialmente. O Streamlit grava uploads em `/tmp` e envia paths via POST, assumindo filesystem compartilhado. O `InMemoryStore` que guarda parent chunks não sobrevive a restarts. Leitura de coleções grandes no Chroma estoura limites do SQLite.

O sistema roda em container único (FastAPI + Streamlit) com volumes Docker para Chroma e sources. Não há requisito de multi-tenancy ou alta disponibilidade.

## Goals / Non-Goals

**Goals:**
- Desacoplar upload de processamento: arquivos chegam via multipart, processamento é async
- Reduzir latência de ingestão batching embeddings por camada em vez de por arquivo
- Persistir parent chunks em disco para sobreviver a restarts
- Tornar leitura de metadados resiliente a coleções grandes via paginação

**Non-Goals:**
- Migrar para banco relacional (Postgres) para o docstore
- Paralelizar embedding via múltiplas workers/processos
- Suportar formatos além de markdown
- Migrar de Chroma para outro vector store
- Implementar websockets para progress (polling é suficiente)

## Decisions

### 1. Upload multipart direto na API

O endpoint `POST /documents/upload` recebe arquivos via `multipart/form-data` (FastAPI `UploadFile`). A API salva os bytes em `data/sources/{filename}` e retorna `202` com `job_id`. O Streamlit não toca mais no filesystem local.

**Alternativa considerada**: manter POST de paths e resolver via volume compartilhado. Descartado porque acopla deploy a filesystem shared e quebra se os serviços forem separados.

### 2. Pipeline por camada

A ingestão deixa de processar arquivo por arquivo e passa a operar em fases sobre o batch completo:

```
Phase 1: PARSE    ─ UnstructuredMarkdownLoader em cada arquivo → List[Document]
Phase 2: SPLIT    ─ parent_splitter + child_splitter sobre todos os docs
Phase 3: EMBED    ─ OpenAIEmbeddings.embed_documents() nos child chunks, em sub-batches
Phase 4: STORE    ─ Chroma collection.add() com embeddings pré-computados (batched)
                    LocalFileStore.mset() para parents
```

Isso desacopla do `ParentDocumentRetriever.add_documents()` na ingestão. O retriever continua sendo usado na busca (retrieve path), mas a ingestão manipula vectorstore e docstore diretamente.

**Alternativa considerada**: manter `ParentDocumentRetriever.add_documents()` e só reduzir batch size. Descartado porque o retriever encapsula embed+store numa chamada, impossibilitando batching cross-arquivo de embeddings.

### 3. LocalFileStore para parent chunks

`InMemoryStore` → `LocalFileStore(root_path="./data/docstore")`. O `LocalFileStore` implementa `BaseStore` do LangChain e persiste cada parent chunk como arquivo em disco, keyed por ID. O `ParentDocumentRetriever` usa `mget(ids)` na busca, que vira leitura de arquivos individuais.

**Alternativa considerada**: segunda collection no Chroma para parents. Descartado porque Chroma não implementa `BaseStore` nativamente e um wrapper adicionaria complexidade sem ganho (parents são acessados por ID, não por similarity search).

**Alternativa considerada**: `PostgresStore` do LangGraph. Descartado porque adiciona dependência de banco relacional para um caso de uso que é simplesmente key-value get/set. Desproporcional para o volume de dados.

### 4. Paginação nas leituras do Chroma

`_collection.get(limit=1000, offset=N)` em loop para listagem de metadados e detecção de duplicatas, em vez de `vs.get()` sem limite que puxa tudo de uma vez.

### 5. Progresso por fase

O `IngestionJob` reporta progresso por fase do pipeline (parsing 3/5 files, embedding 450/2000 chunks, etc.) em vez de por arquivo. Isso reflete melhor o trabalho real em andamento e permite a UI mostrar progresso mais granular durante a fase de embedding, que é a mais demorada.

## Risks / Trade-offs

**[Falha no meio do pipeline perde trabalho parcial]** → Se o embedding falha no chunk 500 de 2000, os 499 anteriores já foram computados mas não armazenados. Mitigação: store em sub-batches durante a Phase 4 (a cada 100 chunks), não tudo no final. Phase 3 (embed) também opera em sub-batches e pode retomar do ponto de falha.

**[LocalFileStore cria muitos arquivos pequenos]** → Cada parent chunk vira um arquivo. Um livro grande pode gerar centenas de parents. Para o volume do CapaRAG (dezenas de livros), isso gera milhares de arquivos, não milhões. Filesystem handles sem problema. Se escalar significativamente, migrar para SQLite-backed store.

**[Desacoplamento do ParentDocumentRetriever na ingestão]** → O retriever continua sendo usado na busca, mas a ingestão passa a manipular vectorstore e docstore diretamente. Isso cria dois caminhos de escrita que precisam ser consistentes (IDs dos parents no metadata dos children). Mitigação: encapsular a lógica de ingestão por camada numa função que garante a consistência de IDs, com testes específicos para isso.

**[Upload multipart com arquivos grandes]** → FastAPI carrega o arquivo inteiro em memória via `UploadFile`. Para livros de RPG em markdown, o tamanho é tipicamente < 5MB. Não é problema. Se no futuro precisar suportar arquivos muito grandes, migrar para streaming upload.

## Open Questions

- Limite de tamanho de batch para embedding da OpenAI: a API aceita até 2048 inputs por chamada para `text-embedding-3-large`. Definir sub-batch size ideal (proposta: 500 chunks por chamada).
- Formato de progresso para o frontend: o Streamlit precisa saber fase atual + progresso dentro da fase. Definir contrato do endpoint de progress.
