## 1. Pipeline core

- [x] 1.1 Create `_process_single_file` function that runs parse → split → [contextualize] → [entity extract+store] → embed+store for one file
- [x] 1.2 Create `_embed_and_store` function that embeds and stores chunks in batches without accumulating all embeddings
- [x] 1.3 Rewrite `run_layered_pipeline` to loop over files calling `_process_single_file`, with progress at file level
- [x] 1.4 Remove unused `_phase_embed` and `_phase_store` as separate functions

## 2. Tests

- [x] 2.1 Update `tests/test_pipeline.py` to cover per-file processing and streaming embed+store
- [x] 2.2 Verify all existing tests still pass

## 3. Verification

- [x] 3.1 Run full test suite and confirm zero regressions
