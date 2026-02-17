## Why

O pipeline atual faz retrieval em uma única passada: expande a pergunta em variações, busca tudo em paralelo, e sintetiza. Isso funciona para perguntas que vivem dentro de um único contexto, mas falha quando a resposta depende de regras distribuídas entre livros ou que se afetam mutuamente. Uma pergunta sobre "Trained by a Master no combate" exige que o sistema primeiro encontre a vantagem, perceba que ela referencia regras de combate cinemático, e vá buscar essas regras em seguida. O sistema atual não faz isso porque o retrieval é cego ao conteúdo que recuperou.

## What Changes

- Introduzir uma abstração de estratégia de retrieval, permitindo trocar o comportamento de busca sem alterar o resto do grafo
- Implementar uma estratégia de multi-hop retrieval: o sistema busca, analisa o que encontrou, decide se precisa de mais contexto, e faz novas buscas até considerar que tem material suficiente
- Refatorar o pipeline atual (multi-question + retrieve) como uma estratégia concreta atrás da mesma interface
- Multi-hop será o default; multi-question continua disponível como alternativa

## Capabilities

### New Capabilities
- `retrieval-strategy`: Interface abstrata para estratégias de retrieval. Define o contrato que qualquer estratégia deve cumprir (receber state, popular contexto, devolver state atualizado). Inclui as duas implementações concretas: MultiQuestionStrategy (comportamento atual) e MultiHopStrategy (busca iterativa com critério de parada por suficiência de contexto).

### Modified Capabilities
<!-- Nenhuma capability existente tem mudança de requisitos no nível de spec. As mudanças são internas ao pipeline de retrieval. -->

## Impact

- `caprag/graph.py`: os nós `multi_question` e `retrieve` são substituídos por um único nó que delega para a estratégia selecionada
- `caprag/schemas.py`: possível extensão do State para acomodar metadados de hops (documentos acumulados, número de iterações)
- Custo de API aumenta no default (multi-hop): cada hop inclui uma chamada ao LLM para análise de suficiência
- Sem breaking changes para o usuário final; a interface do Streamlit não muda
