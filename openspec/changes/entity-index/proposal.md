## Why

O multi-hop atual depende de referências explícitas no texto já recuperado para saber que precisa buscar em outros livros. Se o Basic Set não menciona que Martial Arts expande Rapid Strike, o multi-hop nunca descobre. É um catch-22: para saber que precisa buscar em outro livro, precisa primeiro ter recuperado algo daquele livro.

Um entity index resolve isso mapeando conceitos do domínio GURPS (vantagens, desvantagens, manobras, skills, spells, equipment) para os livros e chunks onde aparecem. Na busca, depois do primeiro round de retrieval, o sistema consulta o entity index para encontrar menções cruzadas em outros livros e faz retrieval direcionado.

## What Changes

- SQLite database (`data/entity_index.db`) mapeando entidades para chunks e livros
- Extração de entidades na ingestão via LLM (reusa o contexto já gerado pelo contextual embeddings)
- Consulta ao entity index no multi-hop para descobrir cross-book references antes de precisar achá-las no texto

## Capabilities

### New Capabilities
- `entity-index`: Knowledge graph simplificado em SQLite mapeando entidades GURPS → livros/chunks, com distinção entre definição e referência

### Modified Capabilities
- `batch-ingestion`: Nova fase de entity extraction na ingestão
- `retrieval-strategy`: Multi-hop consulta entity index para cross-book retrieval proativo

## Impact

- Novo módulo `caprag/entity_index.py`: schema SQLite, insert, query
- `caprag/pipeline.py`: Nova fase de entity extraction (pode combinar com contextualização)
- `caprag/strategies/multi_hop.py`: Consulta entity index entre hops para descobrir cross-book mentions
- `caprag/config.py`: `ENTITY_INDEX_PATH` setting
- Reindex obrigatório
