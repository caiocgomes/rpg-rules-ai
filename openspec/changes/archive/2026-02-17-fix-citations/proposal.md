## Why

O sistema retorna o nome do livro no campo `sources` mas o campo `citations` vem vazio ou com conteúdo genérico. O LLM consegue identificar de qual livro veio a informação, mas não extrai os trechos verbatim que fundamentam a resposta. Isso acontece por dois motivos que se reforçam: o prompt de geração não instrui explicitamente o preenchimento de citations, e o contexto injetado concatena parent chunks sem delimitação clara entre documentos, dificultando a extração de quotes pelo modelo.

O resultado é que a resposta perde rastreabilidade. O usuário vê "GURPS Basic Set" nas fontes mas não sabe qual passagem específica sustenta cada afirmação. Para um sistema de RAG sobre regras de RPG, onde a interpretação exata do texto importa, isso compromete a utilidade.

## What Changes

- **Prompt de geração (`DEFAULT_RAG_TEMPLATE`)**: instrução explícita para preencher citations com quotes verbatim do contexto, vinculando cada afirmação a um trecho e sua fonte
- **Formatação do contexto no `generate`** (`graph.py`): delimitação clara entre documentos com numeração e separadores, dando ao LLM referências estruturadas para extrair quotes

## Non-changes

- A estrutura do state que joga todos os docs em `questions[0].context` (multi-hop, linha 107) fica como está. Refatorar para manter associação doc-por-question é um trabalho separado que faz sentido quando houver valor em mostrar ao usuário de qual sub-pergunta veio cada trecho, mas não é necessário para resolver o problema de citations.

## Capabilities

### Modified Capabilities
- `answer-generation`: Prompt passa a exigir citations verbatim. Contexto formatado com delimitadores e numeração por documento.

## Impact

- `caprag/prompts.py`: Reescrita do `DEFAULT_RAG_TEMPLATE` com instruções de citation
- `caprag/graph.py`: `generate()` reformata `docs_content` com numeração e separadores claros entre documentos
- `tests/`: Ajuste de testes que dependem do formato do prompt ou do contexto
