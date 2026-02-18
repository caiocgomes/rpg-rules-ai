# Answer Generation (delta)

## Changes

### Prompt

O `DEFAULT_RAG_TEMPLATE` passa a instruir:
- Inserir `[N]` após cada afirmação factual no campo `answer`
- `N` corresponde ao número do bloco de contexto (`[1] Source: ...`)
- Preencher `citations` com `index`, `quote` (verbatim), e `source` para cada `[N]` usado
- Manter quote na língua original do contexto

### Post-processing

Após structured output do LLM, o `generate` node valida:
1. Extrai `[N]` do texto via regex
2. Remove citations cujo index não aparece no texto
3. Remove marcadores do texto que não têm citation (transforma em texto puro)
