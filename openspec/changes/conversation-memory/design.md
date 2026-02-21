## Context

O sistema atual processa cada pergunta de forma isolada. `services.ask_question(question: str)` invoca o grafo LangGraph sem nenhum estado anterior. O `MessagesState` no `State` existe mas nasce e morre a cada invocação. O resultado é que perguntas de follow-up ("quantos níveis ele tem?", "compara com o anterior") falham porque o retriever recebe queries sem contexto.

O LangGraph já suporta checkpointers nativos que persistem state entre invocações usando `thread_id`. O `MemorySaver` (in-memory) faz exatamente o que precisamos sem adicionar dependências de storage.

## Goals / Non-Goals

**Goals:**
- Permitir conversas com follow-up dentro de uma sessão do browser
- Resolver referências anafóricas ("ele", "esse", "o anterior") via query rewriting
- Manter o retriever eficaz usando queries standalone reescritas
- Dar ao generate acesso ao histórico para respostas coerentes
- Limitar a janela de histórico a 20 pares (pergunta/resposta) para não explodir memória

**Non-Goals:**
- Persistência de conversas em disco ou banco
- Memória cross-sessão (perfil de usuário, preferências)
- Resumo automático de conversas longas
- Autenticação ou multi-tenancy

## Decisions

### 1. Checkpointer: LangGraph MemorySaver

Usar `MemorySaver` do LangGraph como checkpointer do grafo compilado. Ele persiste o `State` (incluindo `messages`) em um dict Python keyed por `thread_id`.

Alternativa considerada: dict manual em `services.py` gerenciando histórico. Rejeitada porque reinventa o que o LangGraph já faz, e o `MessagesState` já está no State.

O grafo passa a ser compilado com `graph_builder.compile(checkpointer=MemorySaver())`. Cada invocação recebe `config={"configurable": {"thread_id": thread_id}}`.

### 2. Novo nó `rewrite` no grafo

Adicionar um nó `rewrite` entre START e `retrieve`. Esse nó:
1. Lê o histórico de messages do state (últimos 20 pares)
2. Se não há histórico (primeira pergunta), passa a query original direto
3. Se há histórico, chama o LLM (model configurável, default `gpt-4o-mini`) com um prompt que recebe histórico + pergunta atual e retorna uma versão standalone da pergunta
4. Armazena a query reescrita em `main_question` para o retrieve usar

O grafo fica: `START → rewrite → retrieve → generate → END`.

Alternativa considerada: fazer o rewrite dentro do retrieve node. Rejeitada porque violaria single responsibility e dificultaria testar/desabilitar o rewrite independentemente.

### 3. Sliding window de 20 pares

O nó `rewrite` e o prompt do `generate` recebem no máximo os últimos 20 pares (40 messages: 20 HumanMessage + 20 AIMessage). Mensagens mais antigas são ignoradas na construção do prompt, mas permanecem no state do checkpointer.

O truncamento acontece na leitura (nos nós), não na escrita. O MemorySaver guarda tudo, mas os nós filtram.

### 4. Thread ID gerado no frontend

O frontend gera um UUID v4 via `crypto.randomUUID()` no carregamento da página. Esse ID é armazenado em uma variável JS e enviado como campo hidden em cada POST do HTMX.

Fechar a aba = perder o thread_id. O server-side ainda terá o state em memória até restart, mas sem o thread_id o client não consegue acessá-lo. Isso é aceitável dado o non-goal de persistência.

A API JSON (`/api/ask`) recebe `thread_id` como campo opcional no body. Se omitido, gera um UUID server-side (backward compatible, cada chamada é isolada como antes).

### 5. Prompt de rewrite

Um prompt simples e direto, sem overthinking:

```
Given the conversation history and a follow-up question, rewrite the question to be
a standalone question that captures all necessary context. If the question is already
standalone, return it unchanged. Return ONLY the rewritten question, nothing else.
```

Usar `gpt-4o-mini` por default (mesmo model do context_model). É um call rápido (~200ms) e barato.

## Risks / Trade-offs

**Latência adicional por pergunta** (~200-500ms do call de rewrite) → Aceitável. Sem rewrite, o retriever falha em follow-ups, o que é pior que 200ms de latência.

**Acúmulo de state em memória** → Mitigado pela natureza volátil (restart limpa tudo) e pelo fato de ser single-user/poucos usuários. Se escalar, trocar MemorySaver por algo com TTL.

**Rewrite pode distorcer a query original** → O prompt instrui a retornar unchanged se a query já é standalone. Em caso de dúvida, o rewrite tende a ser conservador.

**Mudança na assinatura de ask_question** → Breaking change na API interna, mas o campo `thread_id` é opcional na API JSON (backward compatible para clientes existentes).
