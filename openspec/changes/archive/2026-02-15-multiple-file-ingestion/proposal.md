## Why

O fluxo de ingestão atual aceita um arquivo markdown por vez: o usuário faz upload, clica "Ingest", espera o processamento terminar, e repete. Com 10+ rulebooks GURPS para alimentar, isso vira um processo manual tedioso que bloqueia a interface durante cada ingestão. Não existe forma de subir vários arquivos de uma vez, apontar para um diretório, acompanhar progresso, ou gerenciar o que já está indexado (deletar um livro para re-indexar com parâmetros diferentes, por exemplo).

O `reindex_directory()` existe no código mas não está exposto na UI. A detecção de duplicatas funciona por nome de arquivo, mas quando o usuário quer substituir um livro (corrigiu o markdown, mudou parâmetros de chunking), precisa ir direto na API porque a interface não oferece essa operação.

O resultado é que a ingestão, que deveria ser uma operação de setup rápida, exige atenção manual constante e trava a interface enquanto roda.

## What Changes

- Upload de múltiplos arquivos simultâneos na interface Streamlit (batch upload)
- Ingestão de diretório completo via UI, expondo a funcionalidade que já existe em `reindex_directory()` mas sem forçar rebuild do índice inteiro
- Processamento em background: a ingestão roda sem bloquear a interface, com feedback de progresso por arquivo (qual está processando, quantos faltam, erros)
- Gestão de documentos indexados: visualizar livros indexados com metadados (data de ingestão, número de chunks), deletar livros individuais do índice, re-indexar um livro específico
- Refactor do `ingest.py` para suportar callbacks de progresso e operações sobre documentos individuais (delete by book name)

## Capabilities

### New Capabilities

- `batch-ingestion`: Pipeline que aceita lista de arquivos ou path de diretório e processa sequencialmente em background, com report de progresso por arquivo e tratamento de erros parciais (falha em um arquivo não aborta os demais).
- `document-management`: Operações CRUD sobre o índice: listar com metadados, deletar por livro, re-indexar livro individual. Exposto na UI e na API programática.

### Modified Capabilities

- `document-ingestion`: O `ingest_file()` ganha suporte a callback de progresso. O `reindex_directory()` passa a usar o mesmo pipeline de batch com progresso. A lógica de duplicatas ganha opção de force/replace além do skip atual.

## Impact

- A tab Documents do Streamlit muda substancialmente: upload múltiplo, indicador de progresso, e tabela de documentos indexados com ações (delete, re-index).
- O `ingest.py` precisa de novas funções: `delete_book()`, `ingest_files()` (batch), e o `ingest_file()` existente ganha parâmetro `replace: bool` para forçar re-ingestão.
- Processamento em background implica estado compartilhado entre o processo de ingestão e a UI. No Streamlit, isso significa `st.session_state` com threading ou `asyncio`, com as limitações conhecidas do modelo de execução do Streamlit (re-run a cada interação).
- O Chroma não tem delete nativo por metadata filter no langchain wrapper. A implementação de `delete_book()` precisa consultar IDs por metadata e deletar por ID, o que pode exigir acesso direto à collection do Chroma em vez de passar pelo `ParentDocumentRetriever`.
- Formatos além de markdown (PDF, EPUB) ficam fora deste change. A arquitetura de batch e background que sai daqui facilita adicionar novos loaders depois, mas o escopo agora é só `.md`.
