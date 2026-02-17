## ADDED Requirements

### Requirement: Strategy interface for retrieval
O sistema SHALL definir uma classe abstrata `RetrievalStrategy` com um método `async execute(state: State) -> State`. Qualquer estratégia de retrieval MUST implementar essa interface. O método recebe o estado com a pergunta do usuário e MUST retornar o estado com o campo `questions` populado, incluindo documentos de contexto associados a cada pergunta.

#### Scenario: Strategy contract is enforced
- **WHEN** uma nova estratégia é criada sem implementar `execute`
- **THEN** o sistema levanta `TypeError` na instanciação

#### Scenario: Strategy populates state correctly
- **WHEN** qualquer estratégia executa com uma pergunta válida
- **THEN** o estado retornado contém `questions` com pelo menos uma `Question` que possui `context` não vazio

### Requirement: MultiQuestionStrategy preserves current behavior
O sistema SHALL oferecer `MultiQuestionStrategy` que implementa o comportamento atual: expande a pergunta do usuário em sub-perguntas via LLM, faz retrieval em paralelo para todas as sub-perguntas, e retorna o estado com contextos populados. A pergunta original MUST ser incluída na lista de sub-perguntas.

#### Scenario: Query expansion and parallel retrieval
- **WHEN** o usuário faz uma pergunta simples (ex: "Qual o custo de Magery 3?")
- **THEN** o sistema gera sub-perguntas variando a formulação, faz retrieval em paralelo, e retorna contextos para cada sub-pergunta incluindo a original

### Requirement: MultiHopStrategy with iterative retrieval
O sistema SHALL oferecer `MultiHopStrategy` que faz retrieval iterativo. Em cada hop, o sistema busca documentos, analisa o conteúdo recuperado junto com a pergunta original, e decide se possui contexto suficiente para responder ou se precisa de buscas adicionais.

#### Scenario: Single hop sufficient
- **WHEN** o usuário pergunta algo contido em um único trecho (ex: "Qual o custo de Magery 3?")
- **THEN** o sistema faz retrieval, o analyzer determina que o contexto é suficiente, e retorna após um único hop

#### Scenario: Multiple hops needed for cross-book rules
- **WHEN** o usuário pergunta sobre uma regra que referencia outras regras em livros diferentes (ex: "Como Trained by a Master interage com as regras de combate?")
- **THEN** o sistema faz retrieval inicial, o analyzer identifica que faltam informações sobre regras de combate referenciadas, gera novas queries, faz retrieval adicional, e repete até considerar o contexto suficiente

#### Scenario: Maximum hop limit prevents infinite loops
- **WHEN** o analyzer nunca considera o contexto suficiente
- **THEN** o sistema para após no máximo 3 hops e segue para geração com o contexto acumulado

### Requirement: Sufficiency analysis via LLM
O sistema SHALL usar um LLM para analisar os documentos recuperados e decidir se o contexto é suficiente. O analyzer MUST retornar uma decisão estruturada contendo: (1) se o contexto é suficiente (boolean), e (2) se não for suficiente, uma lista de novas queries para buscar informação faltante.

#### Scenario: Analyzer identifies missing cross-references
- **WHEN** documentos recuperados contêm referências a outras seções ou livros (ex: "see Powers, p. 100" ou "modified by Rapid Strike")
- **THEN** o analyzer retorna `sufficient: false` e gera queries direcionadas às referências identificadas

#### Scenario: Analyzer confirms sufficiency
- **WHEN** documentos recuperados cobrem todos os aspectos da pergunta sem referências pendentes
- **THEN** o analyzer retorna `sufficient: true` e nenhuma query adicional

### Requirement: Document deduplication across hops
O sistema SHALL deduplicar documentos ao longo dos hops. Um documento com mesmo conteúdo e mesmo livro de origem MUST aparecer apenas uma vez no contexto final passado ao gerador.

#### Scenario: Duplicate documents from different hops
- **WHEN** hop 1 e hop 2 recuperam o mesmo trecho do mesmo livro
- **THEN** o documento aparece apenas uma vez no contexto final

### Requirement: Strategy selection via configuration
O sistema SHALL permitir selecionar a estratégia de retrieval via variável de ambiente `RETRIEVAL_STRATEGY`. Valores aceitos: `multi-hop` (default) e `multi-question`. Qualquer outro valor MUST resultar em erro na inicialização.

#### Scenario: Default strategy
- **WHEN** `RETRIEVAL_STRATEGY` não está definida
- **THEN** o sistema usa `MultiHopStrategy`

#### Scenario: Explicit multi-question selection
- **WHEN** `RETRIEVAL_STRATEGY=multi-question`
- **THEN** o sistema usa `MultiQuestionStrategy`

#### Scenario: Invalid strategy value
- **WHEN** `RETRIEVAL_STRATEGY=invalid-value`
- **THEN** o sistema levanta erro de validação na inicialização
