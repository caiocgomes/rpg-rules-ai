## Context

O CapaRAG ingere livros de RPG (GURPS 4e) como PDFs convertidos para markdown. A conversão atual perde a hierarquia de seções, resultando em chunks que cruzam fronteiras semânticas. Child chunks de 200 chars são pequenos demais para embeddings efetivos. Análise dos 7 PDFs com pymupdf4llm confirmou que headers são detectáveis via formatação (bold ALL-CAPS para L1, italic+bold para L3) e que 94% das 2.848 seções cabem em 4.000 chars.

## Goals / Non-Goals

**Goals:**
- Extrair PDFs preservando hierarquia de seções
- Parents respeitam fronteiras de seção (sem contaminação cross-topic)
- Child chunks grandes o suficiente para embeddings semânticos efetivos (512 chars)
- Retriever retorna documentos suficientes (k=12)
- Chunk sizes configuráveis via settings

**Non-Goals:**
- OCR ou extração de imagens/tabelas dos PDFs
- Suporte a formatos além de PDF e markdown
- Manter compatibilidade com chunks antigos (reindex é aceitável)
- Mudar o modelo de embedding

## Decisions

### 1. pymupdf4llm para extração

Testamos pymupdf4llm e docling. pymupdf4llm extrai texto limpo com formatação bold/italic preservada. docling falhou por conflito de dependências e é mais pesado (OCR, layout analysis) sem ganho proporcional para PDFs de texto puro.

O output do pymupdf4llm precisa de pós-processamento: bold ALL-CAPS lines viram `## HEADER`, italic+bold viram `### Sub-header`. Page footers/headers (linhas com `**COMBAT 99**` ou similar) são removidos.

### 2. Section-aware splitting em duas fases

```
PDF → pymupdf4llm → markdown com headers → MarkdownHeaderTextSplitter → seções
                                                                            │
                                          ┌─────────────────────────────────┘
                                          ▼
                                    seção <= 4000?
                                     /          \
                                   sim           não
                                   /              \
                              parent =         RecursiveCharacterTextSplitter
                              seção inteira    max=4000, overlap=500
                                   \              /
                                    \            /
                                     ▼          ▼
                                  child chunks (512, overlap 100)
                                  dentro de cada parent
```

Fase 1: `MarkdownHeaderTextSplitter` separa por `##` e `###`. Cada seção mantém metadata do header hierárquico.

Fase 2: Seções que excedem 4.000 chars passam por `RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=500)`. Seções menores ficam inteiras.

Fase 3: Cada parent é splitado em children de 512 chars, overlap 100.

### 3. Centralização dos splitter definitions

Hoje `retriever.py` e `pipeline.py` definem splitters independentemente. Criar um módulo `caprag/chunking.py` que exporta `get_parent_splitter()`, `get_child_splitter()`, e `split_sections()`. Ambos os módulos importam dali.

### 4. Settings configuráveis

Novas settings em `config.py`:
- `CHILD_CHUNK_SIZE` (default 512)
- `CHILD_CHUNK_OVERLAP` (default 100)
- `PARENT_CHUNK_MAX` (default 4000)
- `PARENT_CHUNK_OVERLAP` (default 500)
- `RETRIEVER_K` (default 12)

### 5. Pipeline de extração PDF

Novo módulo `caprag/extraction.py` com:
- `extract_pdf(path: Path) -> str`: pymupdf4llm → markdown
- `postprocess_headers(md: str) -> str`: heurística de headers
- `clean_page_artifacts(md: str) -> str`: remove page numbers, headers/footers repetidos

O `pipeline.py` chama extraction antes do split. Markdown puro (`.md`) continua sendo aceito sem extração.

## Risks / Trade-offs

**[Heurística de headers pode falhar em livros com formatação diferente]** → A detecção de bold ALL-CAPS funciona nos 7 PDFs GURPS testados. Outros sistemas de RPG podem usar formatação diferente. Mitigação: a heurística é isolada em `postprocess_headers()`, fácil de ajustar por livro ou sistema.

**[Seções muito pequenas geram parents sub-ótimos]** → 67 seções (de 2.848) têm menos de 500 chars. Essas viram parents muito pequenos com 1 child chunk. Aceitável: melhor um parent curto mas semanticamente coerente do que um parent longo que mistura assuntos.

**[Reindex completo obrigatório]** → Chunks antigos são incompatíveis. Precisa deletar chroma + docstore e re-ingerir. Para o volume atual (7 livros), leva minutos.
