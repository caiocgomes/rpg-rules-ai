## Context

O `langchain_chroma.Chroma.add_texts()` delega para `_collection.upsert()` sem dividir em sub-batches. O Chroma calcula `max_batch_size` a partir do `MAX_VARIABLE_NUMBER` do SQLite compilado (tipicamente 32767) dividido por 6 variáveis por registro, resultando em 5461. Quando o `ParentDocumentRetriever` expande 500 docs crus em >5461 child chunks e manda tudo pro `add_texts`, o upsert falha.

O Chroma já oferece `chromadb.utils.batch_utils.create_batches()` que divide operações automaticamente, mas o wrapper do LangChain não usa essa utility.

## Goals / Non-Goals

**Goals:**

- Garantir que nenhuma operação de escrita no Chroma exceda `max_batch_size`, independente do volume de child chunks gerado pelo `ParentDocumentRetriever`
- Solução transparente: nenhuma mudança necessária em `ingest.py`, `ParentDocumentRetriever`, ou UI

**Non-Goals:**

- Otimizar performance de ingestão (paralelismo, async)
- Alterar parâmetros de chunking (child_size, parent_size, overlap)
- Resolver o problema do `InMemoryStore` no `ParentDocumentRetriever`

## Decisions

### Subclass do Chroma com override de `add_texts`

Criar `BatchedChroma(Chroma)` em `caprag/retriever.py` que faz override de `add_texts`. O override consulta `self._collection.count()` ou `_client.get_max_batch_size()` para obter o limite, divide os inputs em sub-batches, e chama `super().add_texts()` para cada sub-batch.

Alternativas consideradas:
- **Monkey-patch do `Chroma.add_texts`**: funciona mas é frágil e dificulta testes.
- **Batch no `_add_in_batches` do `ingest.py`**: não resolve o problema porque o batching acontece antes da expansão de child chunks. Teria que reimplementar a lógica do `ParentDocumentRetriever`.
- **Fork do `langchain_chroma`**: overhead de manutenção desproporcional.

A subclass é o ponto de intervenção mais cirúrgico. O `add_texts` é o método que o `VectorStore.add_documents` chama internamente, então interceptar ali cobre todas as operações de escrita.

### Obter `max_batch_size` via Chroma client

O `max_batch_size` é uma propriedade do `EmbeddingsQueue` do Chroma, acessível via `self._client.get_max_batch_size()` na API do Chroma. O `langchain_chroma.Chroma` expõe `self._client` como atributo público. Não hardcodar 5461 porque o valor depende da versão do SQLite compilada no sistema.

## Risks / Trade-offs

**Acoplamento ao internal API do `langchain_chroma`** — O `self._client` é público no wrapper, mas `get_max_batch_size()` é da API do Chroma, não do LangChain. Se o `langchain_chroma` mudar como expõe o client, o override quebra. Mitigação: a subclass está isolada em `retriever.py`, fácil de adaptar.

**Embeddings calculados por sub-batch** — O `Chroma.add_texts()` calcula embeddings dentro do método. Ao chamar `super().add_texts()` por sub-batch, os embeddings são gerados por sub-batch em vez de todos de uma vez. Na prática, a API da OpenAI já faz batching interno, então o overhead de múltiplas chamadas é negligível comparado ao custo de embedding em si.
