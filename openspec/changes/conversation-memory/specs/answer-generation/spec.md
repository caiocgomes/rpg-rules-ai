## MODIFIED Requirements

### Requirement: Graph topology
O grafo LangGraph SHALL ter a topologia `START → rewrite → retrieve → generate → END`. O grafo SHALL ser compilado com um checkpointer (`MemorySaver`) que persiste state entre invocações por thread_id.

#### Scenario: Grafo com rewrite node
- **WHEN** o grafo é compilado via `build_graph()`
- **THEN** o grafo contém os nós `rewrite`, `retrieve` e `generate` nessa ordem, e possui um checkpointer configurado
