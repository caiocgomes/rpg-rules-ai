## Why

O retriever usa `search_type="similarity"` (default), que retorna os K chunks mais similares à query sem considerar diversidade entre eles. Se os 12 child chunks mais similares vêm todos do mesmo livro, o parent document retrieval retorna 3-4 parents do mesmo livro. Informação relevante em outros livros fica de fora mesmo que esteja no top-30 de similaridade.

Maximal Marginal Relevance (MMR) seleciona chunks iterativamente, penalizando similaridade com chunks já selecionados. Isso força spread entre livros naturalmente: chunks de livros diferentes são mais diversos entre si. O Chroma suporta MMR nativamente e o ParentDocumentRetriever do LangChain aceita `search_type="mmr"`.

## What Changes

- `search_type` do retriever muda de `"similarity"` para `"mmr"`
- `search_kwargs` configurados: `k=12`, `fetch_k=30`, `lambda_mult=0.7`
- Settings configuráveis via `.env`

## Capabilities

### Modified Capabilities
- `retrieval-strategy`: Retriever usa MMR para diversidade de fontes. Busca 30 candidatos, seleciona 12 com balance 70% relevância / 30% diversidade

## Impact

- `caprag/retriever.py`: Adicionar `search_type="mmr"` e `search_kwargs` ao ParentDocumentRetriever
- `caprag/config.py`: `RETRIEVER_FETCH_K` (default 30), `RETRIEVER_LAMBDA_MULT` (default 0.7)
- Zero mudança em pipeline, strategies, frontend ou API
- Não requer reindex (opera sobre o index existente)
