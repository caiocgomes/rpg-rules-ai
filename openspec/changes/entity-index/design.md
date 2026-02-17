## Context

Depende de `section-aware-chunking` e idealmente de `contextual-embeddings` (a extração de entidades pode reusar o contexto gerado). O entity index é um knowledge graph simplificado que mapeia conceitos GURPS para suas localizações no corpus.

## Goals / Non-Goals

**Goals:**
- Mapear entidades do domínio GURPS (vantagens, desvantagens, manobras, skills, spells, etc.) para livros e chunks
- Distinguir "define" (o chunk que explica a regra) de "references" (o chunk que menciona)
- Multi-hop usa o index para cross-book retrieval proativo
- Queries como "onde mais essa entidade aparece?" são O(1) via SQL

**Non-Goals:**
- Knowledge graph completo com relações tipadas entre entidades (GraphRAG, HippoRAG)
- Neo4j ou graph database
- Extração de relações entre entidades (apenas entidade → localização)
- Reasoning sobre o grafo (PageRank, community detection)

## Decisions

### 1. Schema SQLite

```sql
CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,            -- "Rapid Strike", "Enhanced Time Sense"
    normalized TEXT NOT NULL,       -- "rapid_strike", "enhanced_time_sense"
    entity_type TEXT NOT NULL       -- "advantage", "disadvantage", "maneuver", "skill", "spell", "equipment", "modifier", "other"
);

CREATE TABLE entity_mentions (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER REFERENCES entities(id),
    book TEXT NOT NULL,             -- "GURPS 4e - Martial Arts"
    chunk_id TEXT NOT NULL,         -- parent doc_id
    mention_type TEXT NOT NULL,     -- "defines" or "references"
    context TEXT                    -- 1-2 sentence excerpt around the mention
);

CREATE INDEX idx_entity_name ON entities(normalized);
CREATE INDEX idx_mention_entity ON entity_mentions(entity_id);
CREATE INDEX idx_mention_book ON entity_mentions(book);
```

Normalização: lowercase, espaços → underscore, remoção de artigos. Permite matching fuzzy na busca.

### 2. Extração de entidades via LLM

Na ingestão, para cada parent chunk, o LLM extrai entidades mencionadas com tipo e mention_type:

```
Given this passage from {book_name}:
{parent_text}

Extract all GURPS game entities mentioned (advantages, disadvantages, skills,
techniques, maneuvers, spells, equipment, modifiers). For each, indicate:
- name: exact name as written
- type: advantage/disadvantage/skill/technique/maneuver/spell/equipment/modifier/other
- mention_type: "defines" if this passage explains/defines the entity, "references" if it just mentions it

Return as JSON array.
```

Pode rodar na mesma batch de contextualização (mesma chamada LLM, output estruturado diferente) ou como chamada separada. Chamada separada é mais limpa e permite toggle independente.

### 3. Cross-book retrieval no multi-hop

Após cada hop, o multi-hop:
1. Extrai entidades dos chunks recuperados (pode ser via SQL lookup pelo chunk_id, ou via NER leve no texto)
2. Consulta `entity_mentions` para achar outras ocorrências em livros diferentes
3. Se encontra menções em livros que ainda não apareceram no contexto, gera queries direcionadas: "retrieve chunks from {book} about {entity}"
4. O retriever aceita um filtro `where={"book": book_name}` no Chroma

Isso transforma o multi-hop de reativo (esperar referência explícita) para proativo (saber onde procurar antes de achar).

### 4. Maintenance

Quando um livro é deletado (`delete_book()`), os entity_mentions daquele livro são removidos. Entidades que ficam sem nenhuma mention são removidas (garbage collection).

Quando um livro é re-ingerido, mentions antigas são deletadas antes de inserir as novas.

## Risks / Trade-offs

**[Qualidade da extração de entidades]** → gpt-4o-mini pode miss entidades obscuras ou criar falsos positivos. Mitigação: o entity index é uma heurística de discovery, não a fonte de verdade. Falsos positivos geram um retrieval extra que o LLM descarta; falsos negativos significam que o cross-book fallback não funciona para aquela entidade, voltando ao comportamento atual.

**[Tamanho do index]** → Estimativa: ~500-2000 entidades únicas, ~5000-15000 mentions para 7 livros GURPS. SQLite lida com isso sem problemas.

**[Custo de extração]** → Uma chamada LLM por parent chunk (~5000 parents total). Similar ao custo da contextualização. ~$0.50 total com gpt-4o-mini.
