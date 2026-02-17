## Context

A ingestão atual processa um arquivo por vez de forma síncrona, bloqueando a interface Streamlit durante o processamento. O `ingest_file()` recebe um path, carrega com `UnstructuredMarkdownLoader`, chunka via `ParentDocumentRetriever`, e persiste no Chroma. A detecção de duplicatas compara o filename contra metadados já indexados. O `reindex_directory()` existe mas não está exposto na UI.

O `ParentDocumentRetriever` usa um `InMemoryStore` como docstore, o que significa que os parent documents não persistem entre restarts. O Chroma persiste os child chunks com embeddings, mas a relação parent-child se perde quando o processo morre. Isso é um problema pré-existente que afeta a qualidade do retrieval, mas está fora do escopo deste change.

O Chroma suporta `collection.delete(where={"book": book_name})` na API nativa, mas o wrapper do LangChain (`langchain_chroma.Chroma`) expõe `delete(ids=...)` apenas por IDs explícitos. Para deletar por metadata, precisamos acessar a collection subjacente.

## Goals / Non-Goals

**Goals:**

- Permitir upload e ingestão de múltiplos arquivos em uma única operação
- Processar ingestão em background sem bloquear a UI
- Dar visibilidade do progresso: arquivo atual, fila, erros
- Permitir deletar livros individuais do índice
- Permitir re-indexar um livro específico (delete + re-ingest)

**Non-Goals:**

- Suporte a formatos além de markdown (PDF, EPUB ficam para change futuro)
- Resolver o problema do InMemoryStore no ParentDocumentRetriever (pré-existente)
- Upload via API REST ou CLI (só Streamlit por agora)
- Ingestão paralela de múltiplos arquivos simultâneos (processamento é sequencial dentro do batch, o que já é suficiente dado o gargalo de embedding API)

## Decisions

### Background processing via threading + session state

O Streamlit re-executa o script inteiro a cada interação. Para processar em background sem bloquear, a ingestão roda em uma `threading.Thread` separada. O estado do job (progresso, erros, arquivo atual) fica num objeto compartilhado referenciado via `st.session_state`. A UI consulta esse estado a cada re-run e mostra o progresso.

Alternativas consideradas:
- **asyncio**: O Streamlit não tem event loop persistente entre re-runs, então asyncio puro não ajuda.
- **Celery / task queue**: Overhead desproporcional para o caso de uso. Adicionaria Redis ou broker como dependência.
- **subprocess**: Complicaria a comunicação de progresso e o acesso ao Chroma (que usa SQLite internamente e não lida bem com acesso multi-processo).

A thread compartilha o processo do Streamlit, então tem acesso direto ao Chroma. O GIL não é problema porque o gargalo é I/O (chamadas à API de embedding da OpenAI).

### Delete via Chroma collection nativa

Para deletar um livro, acessamos `vectorstore._collection.delete(where={"book": book_name})` em vez de passar pelo wrapper do LangChain. O wrapper só aceita delete por IDs, e consultar todos os IDs de um livro para depois deletar um a um é ineficiente e propenso a race conditions.

Alternativa considerada:
- **Query IDs + delete by IDs**: Funciona mas requer duas operações (get IDs, delete) e não é atômico. O `where` filter no Chroma nativo é uma operação única.

O acesso ao `_collection` é um acesso a atributo interno, mas é estável na API do `langchain_chroma` e não há alternativa pública.

### Persistência dos arquivos fonte

Durante a ingestão, o sistema copia o arquivo markdown original para `./data/sources/{filename}`. Esse diretório funciona como fonte de verdade para re-indexação: quando o usuário pede re-index de um livro, o sistema já tem o arquivo, deleta os vetores pelo metadata `book`, e re-processa a partir da cópia local. Não depende do usuário re-fazer upload.

O path de storage é configurável via `SOURCES_DIR` no `.env` (default: `./data/sources`). Em deploy Docker, o diretório é montado como volume junto com o Chroma.

Alternativas consideradas:
- **Guardar o conteúdo no próprio Chroma como metadata**: Chroma não é feito para armazenar documentos grandes em metadata. Performance degrada e o backup/restore fica acoplado.
- **Não guardar e exigir re-upload**: Funciona, mas frustra o caso de uso principal de re-index (mudou parâmetros de chunking, quer re-processar tudo). O usuário teria que manter os arquivos organizados por conta própria.

O custo de storage é desprezível: um rulebook GURPS em markdown ocupa ~1-2 MB. Mesmo com 20 livros, são ~40 MB.

### Batch ingest como função independente

Nova função `ingest_files(paths, on_progress, replace)` que itera sobre a lista de paths, chama `ingest_file()` para cada um, e invoca o callback `on_progress` com status por arquivo. Erros em um arquivo são capturados e reportados sem abortar os demais.

O `ingest_file()` existente ganha um parâmetro `replace: bool = False`. Quando `replace=True`, deleta o livro existente antes de re-indexar, em vez de pular por duplicata. Em ambos os casos (ingestão nova ou replace), o arquivo fonte é copiado/sobrescrito em `SOURCES_DIR`.

### Ingestão de diretório via UI

A UI oferece um campo de texto para path de diretório local. Ao submeter, lista os `.md` no diretório e alimenta o pipeline de batch. Não usa `st.file_uploader` para diretórios porque o Streamlit não suporta upload de pastas.

Alternativa considerada:
- **st.file_uploader com accept_multiple_files=True**: Funciona para upload múltiplo de arquivos individuais, e será oferecido em paralelo. Mas para diretórios locais (caso de uso principal: apontar para uma pasta com os rulebooks), é necessário o campo de path.

Ambas as opções coexistem: upload múltiplo de arquivos via drag-and-drop E input de diretório local.

## Risks / Trade-offs

**Thread safety do Chroma/SQLite** — O Chroma usa SQLite internamente. SQLite suporta leituras concorrentes mas não escritas concorrentes. Como a ingestão roda em thread separada enquanto a UI pode disparar queries, existe risco teórico de lock contention. Mitigação: a ingestão é a única operação de escrita, e queries são leitura. SQLite em WAL mode (default do Chroma) permite leitura concorrente com escrita.

**Perda de progresso se o processo Streamlit morrer** — Se o usuário fechar o browser ou o processo crashar durante ingestão, os arquivos já processados estão persistidos no Chroma mas os pendentes são perdidos. Mitigação: o progresso mostra claramente quais arquivos já foram processados, facilitando re-run dos faltantes. Não vale a pena implementar job persistence para esse caso de uso.

**Acesso a `_collection` do Chroma** — Atributo interno que pode mudar em versões futuras do `langchain_chroma`. Mitigação: encapsular o acesso numa função `delete_book()` no `ingest.py`, isolando o ponto de quebra potencial.

**Path de diretório local no Streamlit** — Se o deploy for remoto (Docker), o path de diretório se refere ao filesystem do container, não da máquina do usuário. Para o uso atual (local), não é problema. Para deploy remoto, o upload múltiplo via `st.file_uploader` continua funcionando.

**Consistência entre sources e index** — Se o usuário deletar um livro do índice, a cópia em `data/sources/` permanece (permite re-ingest futuro). Se deletar o arquivo de sources manualmente, o re-index via UI falha com mensagem clara. Não existe sync automático entre os dois; a source of truth para "o que está indexado" é o Chroma, e a source of truth para "o que pode ser re-indexado" é o diretório de sources.
