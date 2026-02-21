## MODIFIED Requirements

### Requirement: Ask endpoint
O sistema SHALL expor `POST /ask` que recebe uma pergunta em texto e um `thread_id` opcional, e retorna uma resposta estruturada com answer, sources, citations e see_also. O endpoint SHALL executar o grafo LangGraph completo (rewrite + retrieve + generate). Se `thread_id` for omitido, o endpoint SHALL gerar um UUID internamente, mantendo backward compatibility (cada chamada isolada).

#### Scenario: Pergunta com contexto disponível
- **WHEN** o cliente envia `POST /ask` com body `{"question": "How does Magery work?"}`
- **THEN** o sistema retorna status 200 com body contendo `answer` (string), `sources` (lista de strings), `citations` (lista de objetos com `quote` e `source`), e `see_also` (lista de strings)

#### Scenario: Pergunta com thread_id
- **WHEN** o cliente envia `POST /ask` com body `{"question": "Quantos níveis?", "thread_id": "abc-123"}`
- **THEN** o sistema usa o histórico do thread abc-123 para reescrever a query e gerar a resposta

#### Scenario: Pergunta sem documentos indexados
- **WHEN** o cliente envia `POST /ask` e não há documentos no vector store
- **THEN** o sistema retorna status 200 com uma resposta indicando que não tem informação suficiente
