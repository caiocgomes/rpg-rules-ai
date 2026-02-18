## ADDED Requirements

### Requirement: Aba de edição de prompts
O sistema SHALL exibir uma aba "Prompts" na interface Streamlit onde o usuário pode visualizar e editar os prompts ativos do sistema.

#### Scenario: Visualizar prompts atuais
- **WHEN** o usuário navega para a aba "Prompts"
- **THEN** a interface exibe um `text_area` para cada prompt (RAG e Multi-Question) com o conteúdo atualmente em uso, e indica quais variáveis cada prompt espera receber

#### Scenario: Editar e salvar prompt
- **WHEN** o usuário modifica o texto de um prompt e clica "Salvar"
- **THEN** o prompt é persistido em `data/prompts/` e a próxima pergunta feita no Chat usa o prompt atualizado

#### Scenario: Resetar prompt ao default
- **WHEN** o usuário clica "Reset" em um prompt
- **THEN** o arquivo local é removido, o text_area volta a exibir o default do código, e a próxima pergunta usa o default
