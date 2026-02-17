## 1. Formatação do contexto

- [x] 1.1 Alterar `generate()` em `caprag/graph.py` para formatar `docs_content` com numeração sequencial `[N]`, linha `Source: {book}` e separador `---` entre documentos
- [x] 1.2 Verificar que documentos duplicados (mesmo conteúdo, mesmo book) não geram blocos repetidos no contexto formatado

## 2. Prompt de geração

- [x] 2.1 Reescrever `DEFAULT_RAG_TEMPLATE` em `caprag/prompts.py` com instrução explícita para preencher citations com quotes verbatim do contexto, vinculando cada afirmação factual a um trecho e sua fonte
- [x] 2.2 Ajustar a instrução de concisão para não conflitar com o preenchimento de citations (citations vivem no structured output, não no corpo do answer)

## 3. Testes

- [x] 3.1 Atualizar testes existentes que dependem do formato do prompt ou do contexto
- [x] 3.2 Adicionar teste que verifica o formato numerado do contexto (blocos `[N]`, separadores, `Source:`)

## 4. TODO futuro (não implementar agora)

- [x] 4.1 Documentar no código (comentário em `multi_hop.py:107`) que a atribuição de todos os docs a `questions[0].context` é candidata a refactor para manter associação doc-por-question
