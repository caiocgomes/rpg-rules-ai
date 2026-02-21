## ADDED Requirements

### Requirement: Query rewriting with conversation history
O sistema SHALL reescrever a pergunta do usuário usando o histórico da conversa antes de executar o retrieval. A query reescrita SHALL ser standalone, incorporando referências anafóricas e contexto implícito da conversa. Se a pergunta já for standalone (incluindo a primeira pergunta de uma sessão), SHALL retorná-la sem modificação.

#### Scenario: Rewrite de follow-up com referência anafórica
- **WHEN** o histórico contém "O que é Rapid Strike?" → resposta, e o usuário pergunta "Quantos níveis ele tem?"
- **THEN** o nó rewrite produz "Quantos níveis tem Rapid Strike?" (ou equivalente standalone) e o retriever usa essa query

#### Scenario: Primeira pergunta sem histórico
- **WHEN** o usuário faz a primeira pergunta da sessão "O que é Magery?"
- **THEN** o nó rewrite retorna "O que é Magery?" sem modificação

#### Scenario: Pergunta já standalone com histórico existente
- **WHEN** o histórico contém perguntas anteriores e o usuário pergunta "Como funciona o sistema de magia em GURPS?"
- **THEN** o nó rewrite retorna a pergunta sem modificação pois já é autocontida

### Requirement: Sliding window de histórico
O sistema SHALL limitar o histórico de conversa usado nos nós rewrite e generate aos últimos 20 pares (pergunta/resposta). Mensagens mais antigas SHALL ser ignoradas na construção de prompts mas podem permanecer no state interno do checkpointer.

#### Scenario: Conversa com mais de 20 pares
- **WHEN** a sessão tem 25 pares de pergunta/resposta e o usuário faz a 26a pergunta
- **THEN** os nós rewrite e generate recebem apenas os últimos 20 pares como contexto, ignorando os 5 primeiros

#### Scenario: Conversa curta
- **WHEN** a sessão tem 3 pares e o usuário faz a 4a pergunta
- **THEN** os nós rewrite e generate recebem todos os 3 pares como contexto

### Requirement: Session memory via thread ID
O sistema SHALL identificar sessões de conversa por um `thread_id` (UUID). O state da conversa SHALL ser mantido em memória no servidor (LangGraph MemorySaver). O state SHALL ser volátil: restart do servidor ou perda do thread_id pelo client limpa a sessão.

#### Scenario: Continuidade dentro de uma sessão
- **WHEN** o client envia 3 perguntas com o mesmo thread_id
- **THEN** cada invocação do grafo tem acesso ao histórico das invocações anteriores daquele thread

#### Scenario: Isolamento entre sessões
- **WHEN** dois clients usam thread_ids diferentes
- **THEN** as conversas são completamente independentes, sem vazamento de histórico

#### Scenario: Volatilidade do state
- **WHEN** o servidor é reiniciado
- **THEN** todas as sessões em memória são perdidas e novas conversas começam do zero
