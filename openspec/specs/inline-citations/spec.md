# Inline Citations

## Overview

Citations numeradas inline no texto da resposta. Cada `[N]` no texto refere a um bloco de citation com quote verbatim e fonte, renderizado abaixo do texto e linkado via âncora.

## Schema

- `Citation.index`: int, 1-based, corresponde ao `[N]` no texto
- `Citation.quote`: str, verbatim do contexto, língua original
- `Citation.source`: str, nome do livro exatamente como indexado
- `AnswerWithSources.answer`: str com marcadores `[N]` inline

## Frontend Rendering

- `[N]` no texto vira `<a href="#cite-N" class="cite-marker">[N]</a>`
- Blocos de citation visíveis abaixo do texto, na ordem de `index`
- Cada bloco: índice + nome do livro + blockquote com verbatim
- Click no marcador faz scroll suave até o bloco e destaca com `:target`

## Graceful Degradation

- Se o LLM não gerar marcadores, citations renderizam como lista simples (comportamento atual)
- Marcadores sem citation correspondente são renderizados como texto puro `[N]`
- Citations sem marcador correspondente no texto são descartadas pelo backend
