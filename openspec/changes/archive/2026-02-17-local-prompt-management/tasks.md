## 1. Extrair prompts atuais do LangSmith Hub

- [x] 1.1 Fazer pull dos prompts `cgomes/rag` e `cgomes/gurps_multi_question` do LangSmith Hub e salvar o conteúdo dos templates como referência para os defaults

## 2. Reescrever caprag/prompts.py

- [x] 2.1 Definir prompts default como constantes `ChatPromptTemplate` no módulo (usando o conteúdo extraído em 1.1)
- [x] 2.2 Implementar leitura de arquivo local (`data/prompts/rag.txt`, `data/prompts/multi_question.txt`) com fallback ao default
- [x] 2.3 Implementar função `save_prompt(name, content)` para gravar prompt em disco e `reset_prompt(name)` para deletar arquivo local
- [x] 2.4 Remover import e uso de `langchain_classic.hub`

## 3. UI de edição de prompts no Streamlit

- [x] 3.1 Adicionar aba "Prompts" no `app.py` com `text_area` para cada prompt, exibindo variáveis esperadas como referência
- [x] 3.2 Implementar botão "Salvar" que chama `save_prompt()` e botão "Reset" que chama `reset_prompt()`

## 4. Verificação

- [x] 4.1 Garantir que `data/prompts/` é criado automaticamente se não existir (no save)
- [x] 4.2 Verificar que o volume Docker em `docker-compose.yml` cobre `data/prompts/`
- [x] 4.3 Atualizar testes existentes para não depender de `hub.pull` mockado
