# Entity Index

## Overview

Knowledge graph simplificado em SQLite mapeando entidades GURPS (vantagens, desvantagens, manobras, skills, etc.) para livros e chunks onde aparecem. Distingue definições de referências. Usado pelo multi-hop para cross-book retrieval proativo.

## Schema

Duas tabelas:
- `entities`: id, name, normalized (lowercase, underscored), entity_type
- `entity_mentions`: entity_id → book, chunk_id, mention_type (defines/references), context excerpt

## Entity Types

advantage, disadvantage, skill, technique, maneuver, spell, equipment, modifier, other

## Extraction

- LLM (gpt-4o-mini) extrai entidades de cada parent chunk
- Output: lista de {name, type, mention_type} por chunk
- Batch com asyncio.gather, similar à contextualização
- Roda na ingestão, após split

## Query Interface

- `query_entity(name) -> list[mentions]`: todas as ocorrências de uma entidade
- `query_cross_book(entity_names, exclude_book) -> list[mentions]`: ocorrências em livros diferentes do atual
- Normalização fuzzy: lowercase, underscore, remoção de artigos

## Multi-Hop Integration

Após cada hop:
1. Extrair entidades dos chunks recuperados (lookup por chunk_id no entity index)
2. Consultar cross-book mentions para entidades encontradas
3. Se existem mentions em livros ausentes do contexto, gerar queries com filtro `where={"book": book_name}` no Chroma

## Lifecycle

- `delete_book()` remove entity_mentions do livro + garbage collect entidades órfãs
- Reindex recria todas as mentions

## Configuration

- `ENTITY_INDEX_PATH` (default `data/entity_index.db`)
