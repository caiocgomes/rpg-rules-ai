# MMR Retrieval

## Overview

Retriever usa Maximal Marginal Relevance para diversidade nos resultados. Busca um pool amplo de candidatos e seleciona iterativamente balanceando relevância e diversidade.

## Configuration

- `search_type`: "mmr" (hardcoded, não configurável)
- `RETRIEVER_K`: final selection count (default 12)
- `RETRIEVER_FETCH_K`: candidate pool size (default 30)
- `RETRIEVER_LAMBDA_MULT`: relevance/diversity balance, 0=max diversity, 1=pure similarity (default 0.7)

## Behavior

MMR opera nos child chunks no Chroma. O ParentDocumentRetriever expande children selecionados para parents via docstore lookup. Deduplicação de parents acontece naturalmente (múltiplos children do mesmo parent resultam em um parent no resultado).

## Impact

Não requer reindex. Opera sobre qualquer index existente. Zero mudança em pipeline, strategies, frontend ou API.
