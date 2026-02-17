## Why

Mesmo com section-aware chunking, child chunks de 512 chars podem perder contexto sobre onde estão e do que tratam. Um child chunk que diz "See also Martial Arts, p.127 for expanded options" gera um embedding sobre "referência a outro livro", não sobre "Rapid Strike" que é o assunto real da seção. O embedding não codifica o contexto do parent.

Contextual Retrieval (técnica documentada pela Anthropic, set/2024) resolve isso: na ingestão, um LLM gera um parágrafo curto situando o chunk no contexto do documento, e esse parágrafo é prepended ao chunk antes do embedding. O embedding passa a codificar "esta passagem faz parte da descrição de Rapid Strike no GURPS Basic Set e referencia expansões em Martial Arts". Anthropic reporta 49-67% de redução em falhas de retrieval.

## What Changes

- Na ingestão, após o split em children, cada child recebe um "context prefix" gerado por LLM
- O context prefix é concatenado ao child text antes do embedding
- O child text original (sem prefix) é o que vai para o docstore e para a geração de respostas
- O context prefix é armazenado como metadata do child chunk para auditoria

## Capabilities

### New Capabilities
- `contextual-enrichment`: Enriquecimento de child chunks com contexto do parent via LLM antes do embedding

### Modified Capabilities
- `batch-ingestion`: Nova fase entre split e embed: contextualização. Adiciona chamadas LLM na ingestão (custo one-time)

## Impact

- `caprag/pipeline.py`: Nova Phase 2.5 (contextualize) entre split e embed. Batch de chamadas LLM para gerar context prefixes
- `caprag/config.py`: `CONTEXT_MODEL` setting (default `gpt-4o-mini`), `ENABLE_CONTEXTUAL_EMBEDDINGS` toggle
- `caprag/prompts.py`: Prompt template para contextualização
- Custo de ingestão aumenta (1 chamada LLM por child chunk, ~milhares por livro, gpt-4o-mini)
- Reindex obrigatório
