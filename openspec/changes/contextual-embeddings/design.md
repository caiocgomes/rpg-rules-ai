## Context

Depende da mudança `section-aware-chunking` (child 512, parent 4000, section-aware split). Os child chunks já são maiores e os parents respeitam fronteiras de seção. O contextual embedding adiciona uma camada de enriquecimento semântico aos embeddings.

## Goals / Non-Goals

**Goals:**
- Embeddings de child chunks codificam contexto do parent (assunto, livro, relações cross-book)
- Context prefix não contamina a resposta final (só usado para embedding)
- Custo de contextualização proporcional ao tamanho do corpus (gpt-4o-mini, batch)
- Toggle para desabilitar (permite comparar qualidade com/sem)

**Non-Goals:**
- Trocar o modelo de embedding
- Late Chunking (requer modelo de embedding diferente)
- Propositions/Dense X (complexidade desproporcional para o ganho)

## Decisions

### 1. Prompt de contextualização domain-aware

O prompt recebe book_name, section_headers (do metadata do MarkdownHeaderTextSplitter), parent text e child text. Gera 2-3 frases situando o chunk:

```
Given this section from {book_name}, under the heading "{section_headers}":

<parent>
{parent_text}
</parent>

Write 2-3 sentences of context for this specific passage. Explain what rule, mechanic, or concept it covers, and note any cross-references to other rules, books, or page numbers mentioned.

<passage>
{child_text}
</passage>
```

O prompt é domain-aware: menciona regras, mecânicas, cross-references. Isso direciona o LLM a gerar contexto útil para retrieval em RPG.

### 2. Context prefix armazenado separadamente

O child chunk no Chroma tem dois campos:
- `page_content`: context_prefix + "\n\n" + original_text (para embedding)
- `metadata.original_text`: texto original sem prefix (para display)
- `metadata.context_prefix`: o prefix gerado (para auditoria)

Na hora da geração (generate node), o contexto passado ao LLM usa `original_text` do metadata, não o `page_content` enriquecido. Isso evita que o context prefix (que pode conter imprecisões do LLM) contamine a resposta.

### 3. Batching com gpt-4o-mini

Contextualização roda em paralelo com `asyncio.gather`, batches de 50 chamadas simultâneas (rate limit safe). Cada chamada é independente. Progress reporting integrado ao pipeline existente.

Modelo configurável via `CONTEXT_MODEL` (default `gpt-4o-mini`). Custo estimado: ~$0.01 por livro de 200 páginas (milhares de chunks × ~200 tokens input/output × $0.15/1M tokens).

### 4. Cache de contextos

Context prefixes são armazenados no docstore junto com o parent. Se um reindex mantém os mesmos parents (mesmo PDF, mesmo split), os contextos podem ser reutilizados sem rechamar o LLM. Hash do parent+child text como chave de cache.

## Risks / Trade-offs

**[LLM pode gerar contexto impreciso]** → gpt-4o-mini pode confabular cross-references que não existem. Mitigação: o context prefix só afeta o embedding space, não a resposta final. Um embedding ligeiramente enviesado é melhor que um embedding sem contexto.

**[Custo de ingestão]** → Cada livro adiciona ~$0.01-0.05 em chamadas LLM. Para 7 livros, <$0.50 total. Aceitável como custo one-time.

**[Latência de ingestão]** → Milhares de chamadas LLM em paralelo. Com batch de 50 e ~200ms por chamada, ~40s por 1000 chunks. Para o volume atual (~5000 chunks total), <4 minutos.
