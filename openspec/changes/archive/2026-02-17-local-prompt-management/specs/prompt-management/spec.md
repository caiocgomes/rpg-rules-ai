## ADDED Requirements

### Requirement: Default prompts no código
O sistema SHALL definir prompts default como `ChatPromptTemplate` em `caprag/prompts.py`, sem dependência de serviços externos. Os prompts default SHALL ser: `rag` (variáveis: `question`, `context`) e `multi_question` (variável: `messages`).

#### Scenario: Sistema inicia sem arquivos de prompt locais
- **WHEN** nenhum arquivo existe em `data/prompts/`
- **THEN** as funções `get_rag_prompt()` e `get_multi_question_prompt()` retornam os defaults definidos no código

### Requirement: Persistência local de prompts editados
O sistema SHALL persistir prompts editados como arquivos texto em `data/prompts/`. O arquivo `data/prompts/rag.txt` corresponde ao prompt RAG e `data/prompts/multi_question.txt` ao prompt de expansão de query.

#### Scenario: Prompt editado é salvo em disco
- **WHEN** o usuário edita o prompt RAG via UI e clica "Salvar"
- **THEN** o conteúdo é gravado em `data/prompts/rag.txt` e a próxima chamada a `get_rag_prompt()` retorna o conteúdo do arquivo

#### Scenario: Prompt editado persiste entre sessões
- **WHEN** o usuário salva um prompt, fecha o browser e reabre o app
- **THEN** o prompt editado continua carregado a partir do arquivo local

### Requirement: Fallback chain de carregamento
O sistema SHALL carregar prompts com a seguinte prioridade: arquivo local em `data/prompts/` se existir, caso contrário o default no código.

#### Scenario: Arquivo local existe
- **WHEN** `data/prompts/rag.txt` existe com conteúdo válido
- **THEN** `get_rag_prompt()` retorna um `ChatPromptTemplate` construído a partir do conteúdo do arquivo

#### Scenario: Arquivo local não existe
- **WHEN** `data/prompts/rag.txt` não existe
- **THEN** `get_rag_prompt()` retorna o default definido no código

### Requirement: Reset ao default
O sistema SHALL permitir resetar um prompt ao valor default, removendo o arquivo local correspondente.

#### Scenario: Usuário reseta prompt ao default
- **WHEN** o usuário clica "Reset" no prompt RAG
- **THEN** o arquivo `data/prompts/rag.txt` é removido e a UI exibe o prompt default
