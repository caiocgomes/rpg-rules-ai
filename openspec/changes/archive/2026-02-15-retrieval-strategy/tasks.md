## 1. Interface e configuração

- [x] 1.1 Criar `caprag/strategies/base.py` com ABC `RetrievalStrategy` e método abstrato `async execute(state: State) -> State`
- [x] 1.2 Adicionar setting `RETRIEVAL_STRATEGY` em `caprag/config.py` com default `multi-hop` e validação de valores aceitos (`multi-hop`, `multi-question`)
- [x] 1.3 Criar factory function que instancia a estratégia correta a partir da config

## 2. MultiQuestionStrategy

- [x] 2.1 Criar `caprag/strategies/multi_question.py` extraindo a lógica atual de `multi_question` + `retrieve` do `graph.py` para dentro do método `execute`
- [x] 2.2 Verificar que o comportamento é idêntico ao pipeline atual (mesmas queries, mesmos resultados)

## 3. MultiHopStrategy

- [x] 3.1 Criar `caprag/strategies/multi_hop.py` com a estrutura do loop: retrieve → analyze → decide
- [x] 3.2 Implementar o analyzer de suficiência: prompt + structured output que retorna `{sufficient: bool, new_queries: list[str]}`
- [x] 3.3 Implementar deduplicação de documentos entre hops (hash de `page_content` + `book`)
- [x] 3.4 Implementar cap de 3 hops como safety net

## 4. Integração no grafo

- [x] 4.1 Refatorar `caprag/graph.py`: substituir nós `multi_question` + `retrieve` por um nó único `strategy` que delega para a estratégia selecionada
- [x] 4.2 Garantir que o nó `generate` funciona sem mudanças (recebe o mesmo formato de `questions` com contexto)

## 5. Testes

- [x] 5.1 Testar que `MultiQuestionStrategy` produz resultados equivalentes ao pipeline original
- [x] 5.2 Testar loop do `MultiHopStrategy`: caso de 1 hop (suficiente de primeira), caso de múltiplos hops, caso de cap atingido
- [x] 5.3 Testar deduplicação de documentos
- [x] 5.4 Testar validação de config (valor inválido levanta erro)
