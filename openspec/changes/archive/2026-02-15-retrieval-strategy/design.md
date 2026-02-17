## Context

O pipeline atual em `caprag/graph.py` usa três nós fixos: `multi_question` (expande a pergunta), `retrieve` (busca em paralelo), `generate` (sintetiza resposta). O retrieval é single-pass: todas as buscas acontecem antes de qualquer análise do conteúdo recuperado. Isso impede o sistema de seguir referências cruzadas entre livros ou perceber que precisa de contexto adicional.

O grafo LangGraph é construído via `StateGraph` com edges fixos entre os nós. O estado carrega `questions: Questions` (lista de perguntas com contexto associado) e `answer: AnswerWithSources`.

## Goals / Non-Goals

**Goals:**

- Abstrair a lógica de retrieval atrás de uma interface comum (Strategy), permitindo trocar o comportamento sem alterar `generate` ou o grafo principal
- Implementar MultiHopStrategy: busca iterativa onde um LLM analisa os documentos recuperados e decide se precisa de mais contexto ou se pode parar
- Preservar o comportamento atual como MultiQuestionStrategy atrás da mesma interface
- Multi-hop como default

**Non-Goals:**

- Roteamento automático entre estratégias (classificador que decide qual usar). Fica pra iteração futura
- Otimização de custo (caching de hops, short-circuit para perguntas simples)
- Mudanças na UI do Streamlit
- Mudanças no retriever (Chroma + ParentDocumentRetriever permanecem como estão)

## Decisions

**1. Strategy como ABC com método único `execute`**

Cada estratégia implementa `async def execute(state: State) -> State`, recebendo o estado com a pergunta e devolvendo o estado com `questions` populado (incluindo contexto). O grafo chama a estratégia selecionada em um único nó que substitui `multi_question` + `retrieve`.

Alternativa considerada: manter nós separados no grafo e usar conditional edges pra rotear. Descartada porque cada estratégia tem número diferente de passos internos (multi-question é 2 nós, multi-hop é um loop de N iterações). Encapsular a lógica dentro da estratégia é mais limpo do que tentar expressar loops variáveis no grafo.

**2. MultiHopStrategy: loop interno com LLM como critério de parada**

O loop funciona assim:
1. Gera queries iniciais a partir da pergunta (similar ao multi_question atual)
2. Faz retrieval
3. Chama o LLM com a pergunta original + documentos acumulados e pede uma decisão estruturada: `{sufficient: bool, new_queries: list[str]}`
4. Se `sufficient`, retorna. Se não, faz retrieval das novas queries e volta ao passo 3

Critério de parada secundário: máximo de 3 hops como safety net pra evitar loops infinitos ou custo descontrolado.

Alternativa considerada: número fixo de hops sem LLM decidindo. Descartada porque não resolve o problema real, que é saber quando o contexto é suficiente.

**3. Documentos acumulados com deduplicação**

Ao longo dos hops, documentos recuperados são acumulados em uma lista. Documentos duplicados (mesmo `page_content` + mesmo `book`) são descartados pra não poluir o contexto do `generate`. A deduplicação é simples: hash do conteúdo + metadata de livro.

**4. Configuração da estratégia via `config.py`**

Nova setting `RETRIEVAL_STRATEGY` com valores `multi-hop` (default) e `multi-question`. A factory em `graph.py` instancia a estratégia correta. Sem necessidade de mudança na UI por agora.

## Risks / Trade-offs

**Custo de API** → Cada hop do multi-hop é uma chamada ao LLM (análise de suficiência) + N chamadas ao embedding (retrieval). No pior caso (3 hops), uma pergunta custa 4x mais que o pipeline atual. Mitigação: limite de 3 hops como cap. Monitoramento via LangSmith.

**Latência** → Hops são sequenciais por natureza (cada um depende do resultado do anterior). Uma pergunta que precisa de 3 hops leva ~3x mais tempo. Mitigação: aceitável por agora, paralelização das queries dentro de cada hop ajuda.

**Qualidade do critério de parada** → O LLM pode decidir que tem contexto suficiente quando não tem, ou pedir hops desnecessários. Mitigação: prompt bem calibrado para a análise de suficiência, e iteração baseada em observação de traces no LangSmith.

**Prompt de suficiência é um novo ponto de falha** → Se o prompt do analyzer estiver mal calibrado, o sistema inteiro degrada. Mitigação: prompt no LangChain Hub (versionado), testável isoladamente.
