## Why

Cada pergunta no sistema é processada de forma isolada. Se o usuário pergunta "O que é Rapid Strike?" e depois "Quantos níveis ele tem?", o retriever busca "quantos níveis ele tem?" sem saber quem é "ele". O resultado é lixo. Conversas com follow-up, comparações e referências anafóricas simplesmente não funcionam.

## What Changes

- Adicionar um nó `rewrite` no grafo LangGraph que reescreve a pergunta do usuário usando o histórico da conversa, produzindo uma query standalone antes do retrieval
- Usar `MemorySaver` (in-memory) do LangGraph como checkpointer, persistindo state por `thread_id` entre invocações
- Passar o histórico (últimos 20 pares pergunta/resposta) como contexto para o nó `generate`
- Alterar `services.ask_question` para aceitar `thread_id`
- Alterar os endpoints `/api/ask` e `/chat/ask` para receber e propagar `thread_id`
- Gerar `thread_id` (UUID) no frontend via JavaScript no carregamento da página; enviá-lo em cada request

Memória é volátil: in-memory no servidor, sem persistência em disco. Fechar o browser ou reiniciar o servidor limpa tudo.

## Capabilities

### New Capabilities
- `conversation-memory`: Manutenção de histórico conversacional por sessão, com query rewriting e sliding window de 20 pares

### Modified Capabilities
- `api`: Endpoints `/api/ask` e `/chat/ask` passam a aceitar `thread_id` para identificar a sessão
- `answer-generation`: O nó generate recebe histórico da conversa como contexto adicional
- `web-interface`: Frontend gera e envia `thread_id` por sessão

## Impact

- `rpg_rules_ai/graph.py`: novo nó `rewrite`, grafo compilado com checkpointer
- `rpg_rules_ai/schemas.py`: campo `chat_history` ou uso direto de `messages` do MessagesState
- `rpg_rules_ai/services.py`: assinatura de `ask_question` muda para incluir `thread_id`
- `rpg_rules_ai/api.py`: `AskRequest` ganha campo `thread_id`
- `rpg_rules_ai/frontend.py`: propaga `thread_id` do form
- `rpg_rules_ai/templates/chat.html`: gera UUID no JS, inclui hidden input
- Dependência nova: `langgraph-checkpoint` (se não vier incluso no langgraph)
