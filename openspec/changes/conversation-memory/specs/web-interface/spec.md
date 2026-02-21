## MODIFIED Requirements

### Requirement: Chat via API
A interface web SHALL gerar um thread_id (UUID) no carregamento da página de chat e enviá-lo em cada pergunta submetida. O thread_id SHALL ser gerado via JavaScript e persistido em variável JS durante a sessão da página. Fechar ou recarregar a página SHALL gerar um novo thread_id.

#### Scenario: Thread ID gerado no carregamento
- **WHEN** o usuário acessa a página de chat
- **THEN** a página gera um UUID via `crypto.randomUUID()` e o armazena para uso em requests subsequentes

#### Scenario: Thread ID enviado com cada pergunta
- **WHEN** o usuário submete uma pergunta via o form de chat
- **THEN** o request HTMX inclui o thread_id como campo do form

#### Scenario: Nova sessão ao recarregar
- **WHEN** o usuário recarrega a página (F5 ou navegação)
- **THEN** um novo thread_id é gerado e a conversa começa do zero
