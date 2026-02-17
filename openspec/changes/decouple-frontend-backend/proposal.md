## Why

O `frontend.py` reimplementa toda a lógica de negócio que já existe no `api.py`: invocação do graph, tracking de jobs de ingestão, gerenciamento de prompts. Cada módulo mantém seus próprios singletons (`_graph`, `_jobs`), o que causa bugs funcionais (job criado via HTMX não é encontrado via API, dois graphs em memória). A arquitetura declarada no CLAUDE.md exige que a JSON API seja o contrato e o frontend seja apenas um consumidor, mas o código atual viola isso sistematicamente.

## What Changes

- Extrair estado compartilhado (`_graph`, `_jobs`) e lógica de orquestração para um módulo `caprag/services.py`
- **BREAKING**: Rotas HTMX do `frontend.py` deixam de ter lógica própria e passam a chamar funções do service layer
- `api.py` passa a ser wrapper JSON fino sobre o service layer (validação HTTP + serialização)
- `frontend.py` passa a ser wrapper HTML/template fino sobre o service layer (renderização + HTMX responses)
- Validação de domínio (extensão de arquivo, path existe) migra para o service layer como exceções Python; cada router traduz para seu formato (HTTPException ou HTMLResponse)
- Upload de arquivos: routers continuam responsáveis por salvar `UploadFile` no disco (conceito FastAPI); service recebe `list[Path]`

## Capabilities

### New Capabilities

- `service-layer`: Módulo de serviço compartilhado (`caprag/services.py`) que centraliza estado e orquestração de chat, documentos e prompts. Singletons de graph e job registry vivem aqui.

### Modified Capabilities

- `web-interface`: As rotas HTMX deixam de conter lógica de negócio e passam a delegar para o service layer. Contrato HTML dos endpoints não muda (mesmos templates, mesmas respostas HTMX).

## Impact

- `caprag/api.py`: remove singletons `_graph`, `_jobs`, `_get_graph()`; importa e delega para `caprag/services`
- `caprag/frontend.py`: remove singletons `_graph`, `_jobs`, `_get_graph()`; remove imports diretos de `caprag.graph`, `caprag.ingest`, `caprag.prompts`; importa e delega para `caprag/services`
- Novo arquivo: `caprag/services.py`
- Sem mudança em dependências externas, schemas, templates, ou endpoints da JSON API
- Requer reinício do servidor após deploy (singletons mudam de módulo)
