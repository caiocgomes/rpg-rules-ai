## Why

O pipeline de ingestão acumula todos os documentos, chunks e embeddings em memória antes de gravar. Num servidor pequeno (1-2GB RAM), subir vários livros de RPG mata o processo por OOM. O serviço recebe SIGKILL do kernel, perde todo o progresso e entra em loop de restart.

## What Changes

- Reestruturar `pipeline.py` para processar um arquivo por vez (parse → split → embed → store), liberando memória entre arquivos
- Fundir as fases embed+store para nunca manter todos os embeddings em RAM simultaneamente: gerar embedding de um batch, gravar, descartar, próximo batch
- Entidades extraídas são gravadas imediatamente por arquivo, sem acumular lista global
- Ajustar progress reporting para refletir processamento per-file com sub-progresso por fase

## Capabilities

### New Capabilities

- `streaming-ingestion`: Pipeline de ingestão com footprint de memória proporcional a um único arquivo, não ao total de arquivos submetidos

### Modified Capabilities

- `batch-ingestion`: O progress callback passa a reportar progresso por arquivo com sub-fases, em vez de fases globais

## Impact

- `rpg_rules_ai/pipeline.py`: reescrita do `run_layered_pipeline` e remoção das funções `_phase_embed`/`_phase_store` separadas
- `rpg_rules_ai/templates/fragments/progress.html`: ajuste mínimo nas strings de progresso (a estrutura do dict de progress não muda)
- `tests/test_pipeline.py`: testes precisam refletir o novo fluxo per-file
- Sem mudança de API externa (mesma interface `run_layered_pipeline(paths, replace, on_progress)`)
