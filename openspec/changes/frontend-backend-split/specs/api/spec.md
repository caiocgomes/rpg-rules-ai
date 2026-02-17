## ADDED Requirements

### Requirement: Ask endpoint
O sistema SHALL expor `POST /ask` que recebe uma pergunta em texto e retorna uma resposta estruturada com answer, sources, citations e see_also. O endpoint SHALL executar o grafo LangGraph completo (retrieve + generate).

#### Scenario: Pergunta com contexto disponível
- **WHEN** o cliente envia `POST /ask` com body `{"question": "How does Magery work?"}`
- **THEN** o sistema retorna status 200 com body contendo `answer` (string), `sources` (lista de strings), `citations` (lista de objetos com `quote` e `source`), e `see_also` (lista de strings)

#### Scenario: Pergunta sem documentos indexados
- **WHEN** o cliente envia `POST /ask` e não há documentos no vector store
- **THEN** o sistema retorna status 200 com uma resposta indicando que não tem informação suficiente

### Requirement: List documents endpoint
O sistema SHALL expor `GET /documents` que retorna a lista de livros indexados com metadata (nome do livro, contagem de chunks, disponibilidade do arquivo fonte).

#### Scenario: Documentos existem
- **WHEN** o cliente envia `GET /documents` e há livros indexados
- **THEN** o sistema retorna status 200 com lista de objetos contendo `book` (string), `chunk_count` (int), `has_source` (bool)

#### Scenario: Nenhum documento
- **WHEN** o cliente envia `GET /documents` e não há livros indexados
- **THEN** o sistema retorna status 200 com lista vazia

### Requirement: Ingest documents endpoint
O sistema SHALL expor `POST /documents/ingest` que recebe uma lista de paths de arquivos markdown e inicia ingestão em background, retornando um job_id para acompanhamento.

#### Scenario: Iniciar ingestão
- **WHEN** o cliente envia `POST /documents/ingest` com body `{"paths": ["/path/to/file.md"], "replace": false}`
- **THEN** o sistema retorna status 202 com body contendo `job_id` (string UUID)

#### Scenario: Path inválido
- **WHEN** o cliente envia `POST /documents/ingest` com um path que não existe
- **THEN** o sistema retorna status 400 com mensagem de erro

### Requirement: Ingestion job progress endpoint
O sistema SHALL expor `GET /documents/jobs/{job_id}` que retorna o progresso de um job de ingestão.

#### Scenario: Job em andamento
- **WHEN** o cliente envia `GET /documents/jobs/{job_id}` para um job running
- **THEN** o sistema retorna status 200 com `status` ("running"), `current_file`, `completed`, `total`, e `results`

#### Scenario: Job inexistente
- **WHEN** o cliente envia `GET /documents/jobs/{job_id}` com um ID que não existe
- **THEN** o sistema retorna status 404

### Requirement: Delete document endpoint
O sistema SHALL expor `DELETE /documents/{book}` que remove todos os chunks de um livro do vector store.

#### Scenario: Deletar livro existente
- **WHEN** o cliente envia `DELETE /documents/BasicSet.md`
- **THEN** o sistema remove os chunks e retorna status 200

### Requirement: Prompts endpoints
O sistema SHALL expor endpoints para gerenciar prompts: `GET /prompts` (listar todos), `GET /prompts/{name}` (conteúdo atual), `PUT /prompts/{name}` (salvar), `DELETE /prompts/{name}` (reset ao default).

#### Scenario: Listar prompts
- **WHEN** o cliente envia `GET /prompts`
- **THEN** o sistema retorna status 200 com lista de objetos contendo `name`, `content`, `variables`, `is_custom` (bool indicando se há arquivo local)

#### Scenario: Salvar prompt editado
- **WHEN** o cliente envia `PUT /prompts/rag` com body `{"content": "novo template com {question} e {context}"}`
- **THEN** o sistema persiste o prompt e retorna status 200

#### Scenario: Reset prompt ao default
- **WHEN** o cliente envia `DELETE /prompts/rag`
- **THEN** o sistema remove o arquivo local e retorna status 200 com o conteúdo default
