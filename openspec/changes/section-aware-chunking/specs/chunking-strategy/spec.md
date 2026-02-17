# Chunking Strategy

## Overview

Section-aware hierarchical chunking que respeita fronteiras semânticas do documento. PDFs são extraídos via pymupdf4llm, pós-processados para reconstituir headers markdown, e splitados em parents/children respeitando limites de seção.

## Extraction

- PDFs extraídos via `pymupdf4llm.to_markdown()`
- Pós-processamento de headers: bold ALL-CAPS standalone lines → `##`, italic+bold lines → `###`
- Page artifacts removidos (page numbers, repeated footers)
- Markdown puro (`.md`) aceito sem extração

## Parent Chunking

- Primeiro split por headers markdown (`MarkdownHeaderTextSplitter`)
- Seções <= `PARENT_CHUNK_MAX` (default 4000 chars) ficam inteiras como parent
- Seções > `PARENT_CHUNK_MAX` passam por `RecursiveCharacterTextSplitter(chunk_size=PARENT_CHUNK_MAX, chunk_overlap=PARENT_CHUNK_OVERLAP)`
- `PARENT_CHUNK_OVERLAP` default 500 chars

## Child Chunking

- `RecursiveCharacterTextSplitter(chunk_size=CHILD_CHUNK_SIZE, chunk_overlap=CHILD_CHUNK_OVERLAP)`
- `CHILD_CHUNK_SIZE` default 512 chars
- `CHILD_CHUNK_OVERLAP` default 100 chars
- Cada child recebe `metadata.doc_id` linkando ao parent

## Retriever

- `k=RETRIEVER_K` (default 12) child chunks recuperados
- Parents expandidos via docstore lookup

## Metadata

- `book`: nome do arquivo fonte (sem extensão)
- `doc_id`: UUID do parent no docstore
- `start_index`: offset do chunk dentro do parent
- `section_headers`: hierarquia de headers do MarkdownHeaderTextSplitter (ex: "## COMBAT > ### Rapid Strike")

## Configuration

Todas as settings via `.env`:
- `CHILD_CHUNK_SIZE` (default 512)
- `CHILD_CHUNK_OVERLAP` (default 100)
- `PARENT_CHUNK_MAX` (default 4000)
- `PARENT_CHUNK_OVERLAP` (default 500)
- `RETRIEVER_K` (default 12)
