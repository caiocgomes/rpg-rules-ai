## Why

Os markdowns atuais são dumps de PDF sem estrutura. O `UnstructuredMarkdownLoader` gera 46.787 fragmentos com mediana de 57 chars que o `RecursiveCharacterTextSplitter` compacta em janelas uniformes de 2000 chars, cortando no meio de seções sem respeitar fronteiras semânticas. Um parent chunk pode começar no meio de "Rapid Strike" e terminar no meio de "Deceptive Attack". Child chunks de 200 chars são tão pequenos que os embeddings perdem contexto semântico e a busca vetorial degrada para quase keyword matching.

Análise empírica dos 7 PDFs com `pymupdf4llm` mostrou que a hierarquia de seções é detectável via heurística (bold ALL-CAPS para seções L1, italic+bold para sub-seções L3). Com granularidade L1+L3, 2.848 seções foram identificadas com mediana de 738 chars. Com parent max de 4.000 chars, 94% das seções cabem inteiras sem character split.

## What Changes

- **BREAKING**: Extração de PDFs via `pymupdf4llm` em vez de markdown pré-processado. Os fontes passam a ser PDFs em `data/pdfs/` (ou `PDFs/`), não markdowns
- Pós-processamento com heurística de headers: bold ALL-CAPS → `##`, italic+bold → `###`
- Split section-aware: primeiro por headers markdown, depois character split para seções > 4.000 chars
- Child chunks: 200 → 512 chars, overlap 40 → 100
- Parent chunks: 2.000 → 4.000 chars max (section-aware, maioria das seções cabe inteira)
- k do retriever: 4 → 12
- Unificação dos splitter definitions (hoje duplicados em `retriever.py` e `pipeline.py`) num único lugar

## Capabilities

### New Capabilities
- `pdf-extraction`: Extração de PDFs via pymupdf4llm com detecção de hierarquia de seções e conversão para markdown estruturado

### Modified Capabilities
- `document-ingestion`: Pipeline aceita PDFs como input, aplica extração estruturada antes do split
- `batch-ingestion`: Splitters section-aware substituem character-only splitting. Parent max 4.000, child 512

## Impact

- `caprag/pipeline.py`: Nova fase de extração PDF → markdown estruturado antes do split. Splitters section-aware
- `caprag/retriever.py`: Novos chunk sizes (child 512/100, parent 4000/500), k=12. Splitter definitions centralizados
- `caprag/config.py`: Novas settings para chunk sizes e k
- `pyproject.toml`: Adicionar `pymupdf4llm` como dependência
- Reindex completo obrigatório (incompatível com chunks antigos)
- `tests/`: Testes para extração PDF, detecção de headers, section-aware splitting
