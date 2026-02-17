## Why

O Chroma usa SQLite internamente e tem um limite de batch derivado do `MAX_VARIABLE_NUMBER` do SQLite: 32767 variáveis / 6 por registro = 5461 documentos por operação. O `ParentDocumentRetriever` do LangChain expande cada batch de documentos crus em child chunks (ratio ~10x com os parâmetros atuais: parents de 2000 chars, children de 200 chars com overlap de 40) e manda tudo pro `Chroma.add_texts()` de uma vez. O `_add_in_batches` atual controla o input (500 docs crus), mas o gargalo é no output (child chunks), que é imprevisível e facilmente ultrapassa 5461. Um rulebook longo sozinho pode gerar mais de 5461 children.

## What Changes

- Subclass do `Chroma` que intercepta `add_texts` e quebra automaticamente em sub-batches respeitando `max_batch_size` do Chroma. Transparente para o resto do código.
- O `INGEST_BATCH_SIZE` deixa de ser a defesa contra o limite do Chroma e passa a ser apenas controle de memória/logging.

## Capabilities

### New Capabilities

- `chroma-auto-batching`: Wrapper do vectorstore Chroma que auto-divide operações de escrita em sub-batches dentro do limite do SQLite.

### Modified Capabilities

## Impact

- `caprag/retriever.py`: `get_vectorstore()` instancia a subclass em vez do `Chroma` vanilla.
- Nenhuma mudança na interface pública. O `ParentDocumentRetriever`, `ingest.py`, e a UI continuam iguais.
- Nenhuma dependência nova.
