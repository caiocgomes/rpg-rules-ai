## Why

O sistema retorna citations como lista solta num accordion colapsado abaixo da resposta, sem vínculo entre cada afirmação no texto e o trecho fonte que a sustenta. Para um sistema de RAG sobre regras de RPG, onde a interpretação exata do texto importa, o usuário precisa ver qual passagem verbatim fundamenta cada afirmação, no local onde ela aparece. O padrão de inline citations numeradas (`[1]`, `[2]`) é familiar (papers, Wikipedia, Perplexity) e resolve isso.

## What Changes

- **Schema `AnswerWithSources`**: `Citation` ganha campo `index: int`. O campo `answer` passa a conter marcadores `[N]` inline referenciando citations pelo índice
- **Prompt de geração (`DEFAULT_RAG_TEMPLATE`)**: instrução para inserir `[N]` no texto do answer e preencher citations com índice correspondente e quote verbatim
- **Backend validation**: sanitização pós-LLM que garante consistência entre marcadores no texto e índices nas citations (dropar citations órfãs, renumerar se necessário)
- **Frontend**: parse de `[N]` no texto como links/âncoras. Citations renderizadas como blocos abaixo do texto, na ordem de referência, com quote verbatim e livro fonte. Click no `[N]` scrolla/destaca o bloco correspondente

## Capabilities

### New Capabilities
- `inline-citations`: Renderização de citations inline numeradas no texto da resposta, com blocos de referência clicáveis mostrando quote verbatim e fonte

### Modified Capabilities
- `answer-generation`: Prompt e schema passam a exigir citations indexadas com marcadores inline no texto

## Impact

- `caprag/schemas.py`: `Citation` ganha `index: int`
- `caprag/prompts.py`: Reescrita do `DEFAULT_RAG_TEMPLATE` com instruções de inline citation
- `caprag/graph.py`: Validação pós-LLM de consistência marcadores/citations
- `caprag/templates/fragments/chat_answer.html`: Renderização de inline citations com blocos de referência
- `caprag/static/style.css`: Estilos para citation markers e blocos
- `tests/`: Testes para validação de citations e novo formato de resposta
