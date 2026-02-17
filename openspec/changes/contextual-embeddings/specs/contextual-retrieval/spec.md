# Contextual Retrieval

## Overview

Na ingestão, cada child chunk recebe um context prefix gerado por LLM que situa o chunk no contexto do documento. O prefix é prepended ao texto antes do embedding mas não é usado na geração de respostas.

## Context Generation

- Input: book_name, section_headers, parent text, child text
- Output: 2-3 frases de contexto (regra/mecânica, livro, cross-references)
- Model: `CONTEXT_MODEL` (default `gpt-4o-mini`)
- Batch: asyncio.gather com batch_size=50

## Storage

- `page_content` no Chroma: context_prefix + "\n\n" + original_text (para embedding)
- `metadata.original_text`: texto original sem prefix (para geração)
- `metadata.context_prefix`: prefix gerado (para auditoria)

## Usage in Generation

O generate node usa `metadata.original_text` quando disponível, fallback para `page_content`. O context prefix nunca aparece na resposta final.

## Toggle

- `ENABLE_CONTEXTUAL_EMBEDDINGS` (default true)
- Quando false, pipeline pula a fase de contextualização e embeds child text puro

## Configuration

- `CONTEXT_MODEL` (default `gpt-4o-mini`)
- `ENABLE_CONTEXTUAL_EMBEDDINGS` (default true)
