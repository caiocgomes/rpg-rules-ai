## Context

O `run_layered_pipeline` em `rpg_rules_ai/pipeline.py` processa todos os arquivos de uma vez: parseia tudo, splitta tudo, gera todos os embeddings em memória, e só então grava. Com 10 livros GURPS (300-500KB cada), o pico de memória facilmente passa de 500MB por conta dos vetores de embedding (24KB cada × milhares de chunks). Num servidor com 1-2GB de RAM total, o OOM killer mata o processo.

A interface pública (`run_layered_pipeline(paths, replace, on_progress)`) não muda. O `IngestionJob` e os endpoints de API continuam iguais.

## Goals / Non-Goals

**Goals:**
- Pico de memória proporcional a um único arquivo, não ao total de arquivos submetidos
- Embeddings nunca ficam todos em RAM: gerar batch, gravar, descartar
- Falha num arquivo não perde o progresso dos anteriores (já parcialmente verdade, agora completo)
- Progress reporting continua funcional na UI

**Non-Goals:**
- Não otimizar o consumo de memória do Chroma em si (carrega index na RAM, é problema separado)
- Não paralelizar ingestão entre arquivos (processamento sequencial é suficiente e previsível)
- Não mudar o schema do dict de progress (mantém compatibilidade com `progress.html`)

## Decisions

**1. Loop per-file em vez de fases globais**

O `run_layered_pipeline` vira um loop que, para cada arquivo, executa parse → split → [contextualize] → [entity extract+store] → embed+store. Cada iteração libera as estruturas do arquivo anterior.

Alternativa considerada: manter fases globais mas com generators/iteradores lazy. Rejeitada porque a complexidade aumenta sem ganho real, já que o gargalo é a acumulação de embeddings que precisam ser consumidos antes de gerar os próximos.

**2. Fundir embed + store numa única função `_embed_and_store`**

Em vez de `_phase_embed` retornar `list[list[float]]` e `_phase_store` consumi-la, a nova `_embed_and_store` faz um loop: pega batch de chunks, chama `embed_documents`, grava no Chroma, descarta os vetores, próximo batch. Memória máxima = O(EMBED_BATCH_SIZE × 24KB).

**3. Entidades gravadas imediatamente por arquivo**

Hoje `_phase_extract_entities` acumula uma lista de resultados e `_phase_store_entities` grava depois. No novo fluxo, a extração e gravação de entidades acontecem dentro do loop per-file, logo após o split. Sem lista global intermediária.

**4. Progress reporting: fase "ingesting" com total = número de arquivos**

A UI hoje mostra "Embedding: 234/5000". Com o novo fluxo, mostra "Ingesting: 3/10" (file-level). As sub-fases (parsing, splitting, embedding) ficam invisíveis no progress dict mas logam no journal. O template `progress.html` funciona sem mudança porque consome `phase`, `phase_completed`, `phase_total` genericamente.

## Risks / Trade-offs

**[Menos granularidade no progress]** → A UI perde visibilidade das sub-fases (embedding 234/5000). Mitigação: para o caso de uso real (upload de livros), saber qual arquivo está processando é mais útil que saber qual chunk está sendo embedded.

**[Mais writes no Chroma]** → Em vez de um grande batch de store no final, faz vários stores menores. Mitigação: o Chroma já recebia batches de 100 via `BatchedChroma`; a mudança não altera o tamanho individual dos batches, só a frequência. Impacto em performance negligível.

**[Entity index abre/fecha por arquivo]** → Hoje abre uma vez e grava tudo. No novo modelo, abre por arquivo. Mitigação: SQLite lida bem com open/close frequente; o custo é desprezível comparado ao LLM call da extração.
