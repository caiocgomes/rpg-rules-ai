## Why

O pipeline de ingestão atual acopla upload, parsing, embedding e storage num fluxo serial por arquivo. O Streamlit grava arquivos em `/tmp` e envia paths para a API, o que quebra quando os serviços rodam em máquinas separadas. O processamento por arquivo gera chamadas pequenas e frequentes à API de embedding, acumulando latência desnecessária. O `InMemoryStore` usado como docstore dos parent chunks perde dados a cada restart do servidor, tornando o `ParentDocumentRetriever` não-funcional após reinício. Além disso, operações de leitura em coleções grandes (listagem, detecção de duplicatas) estouram o limite de variáveis SQL do SQLite no Chroma.

## What Changes

- **BREAKING**: Upload de arquivos passa a ser multipart direto para a API, eliminando dependência de filesystem compartilhado entre Streamlit e FastAPI
- Ingestão muda de pipeline serial por arquivo para pipeline por camada (parse all → split all → embed batch → store batch), reduzindo chamadas à API de embedding
- `InMemoryStore` substituído por `LocalFileStore` persistente em `data/docstore/`, resolvendo perda de parent chunks no restart
- Operações de leitura no Chroma (listagem de livros, detecção de duplicatas) passam a usar paginação para evitar estouro de SQL variables
- Interface Streamlit desacoplada do processamento: upload retorna imediato, processamento é async com polling não-bloqueante

## Capabilities

### New Capabilities
- `file-upload-api`: Endpoint multipart para receber arquivos binários diretamente na API, com storage em `data/sources/`
- `layered-ingestion`: Pipeline de ingestão por camada com batching de embeddings e storage, substituindo o fluxo serial por arquivo
- `persistent-docstore`: Docstore persistente em disco para parent chunks do ParentDocumentRetriever

### Modified Capabilities
- `batch-ingestion`: Processamento muda de serial-por-arquivo para pipeline por camada. Callbacks de progresso passam a reportar por fase (parsing, splitting, embedding, storing) em vez de por arquivo
- `web-interface`: Upload muda de file_uploader + POST de paths para multipart direto à API. Progress display adapta para fases do pipeline
- `document-management`: Listagem e detecção de duplicatas passam a usar paginação no Chroma

## Impact

- `caprag/api.py`: Novo endpoint multipart, modificação do endpoint de ingest
- `caprag/ingest.py`: Reescrita do pipeline de ingestão para operar por camada
- `caprag/retriever.py`: `InMemoryStore` → `LocalFileStore`, batching de storage
- `caprag/ingestion_job.py`: Progresso por fase em vez de por arquivo
- `caprag/schemas.py`: Novos tipos para progresso por fase
- `app.py`: Upload multipart, display de progresso por fase
- `docker-compose.yml`: Novo volume para `data/docstore/`
- `tests/`: Atualização de testes de ingestão, novos testes para upload multipart e docstore persistente
