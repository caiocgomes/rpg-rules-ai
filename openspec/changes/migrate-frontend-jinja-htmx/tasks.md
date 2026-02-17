## 1. Setup e Infraestrutura

- [x] 1.1 Adicionar `jinja2` ao `pyproject.toml` via `uv add jinja2`
- [x] 1.2 Criar diretórios `caprag/templates/`, `caprag/templates/fragments/`, `caprag/static/`
- [x] 1.3 Baixar `htmx.min.js` (v2.x) para `caprag/static/htmx.min.js`
- [x] 1.4 Configurar `Jinja2Templates` e `StaticFiles` no FastAPI app (`caprag/api.py`)

## 2. Base Template e CSS

- [x] 2.1 Criar `caprag/templates/base.html` com nav (Chat, Documents, Prompts), head com Pico CSS CDN + htmx local, block content
- [x] 2.2 Criar `caprag/static/style.css` com overrides mínimos (layout do chat, progress bar)

## 3. Chat Page

- [x] 3.1 Criar `caprag/templates/chat.html` com container de mensagens e form de input
- [x] 3.2 Criar `caprag/templates/fragments/chat_message.html` (fragment de mensagem do usuário)
- [x] 3.3 Criar `caprag/templates/fragments/chat_answer.html` (fragment de resposta com citations, sources, see_also)
- [x] 3.4 Criar rota `GET /` que serve `chat.html`
- [x] 3.5 Criar rota `POST /chat/ask` que processa a pergunta e retorna fragment HTML (mensagem do usuário + resposta)
- [x] 3.6 Configurar HTMX: form envia via `hx-post`, resposta inserida com `hx-swap="beforeend"`, loading indicator

## 4. Documents Page

- [x] 4.1 Criar `caprag/templates/documents.html` com seção de upload, seção de directory ingest, seção de progress, e tabela de docs
- [x] 4.2 Criar `caprag/templates/fragments/doc_list.html` (tabela completa de documentos)
- [x] 4.3 Criar `caprag/templates/fragments/doc_row.html` (linha individual de documento)
- [x] 4.4 Criar `caprag/templates/fragments/progress.html` (progress bar + per-file results)
- [x] 4.5 Criar rota `GET /documents` que serve `documents.html` com lista de docs preenchida
- [x] 4.6 Criar rota `GET /documents/list` (HTMX) que retorna fragment `doc_list.html`
- [x] 4.7 Criar rota `POST /documents/htmx/upload` que faz upload, inicia job, e retorna fragment progress com `hx-trigger="every 2s"` para polling
- [x] 4.8 Criar rota `GET /documents/htmx/progress/{job_id}` que retorna fragment progress atualizado (para polling quando done/error)
- [x] 4.9 Criar rota `DELETE /documents/htmx/{book}` que deleta e retorna fragment vazio + HX-Trigger para refresh da lista

## 5. Prompts Page

- [x] 5.1 Criar `caprag/templates/prompts.html` com lista de prompts, cada um com textarea e botões save/reset
- [x] 5.2 Criar `caprag/templates/fragments/prompt_card.html` (card individual de prompt)
- [x] 5.3 Criar rota `GET /prompts` HTML que serve `prompts.html` (nota: rota JSON existente usa content-type, ou usar path diferente `/prompts/page`)
- [x] 5.4 Criar rota `PUT /prompts/htmx/{name}` que salva e retorna fragment `prompt_card.html` atualizado
- [x] 5.5 Criar rota `DELETE /prompts/htmx/{name}` que reseta e retorna fragment `prompt_card.html` com default

## 6. Frontend Router

- [x] 6.1 Criar `caprag/frontend.py` com APIRouter contendo todas as rotas HTML e HTMX
- [x] 6.2 Montar o router no app FastAPI em `caprag/api.py`
- [x] 6.3 Resolver conflito de rota `GET /documents` e `GET /prompts` (JSON API vs HTML page) usando content negotiation ou prefixo `/api/` para JSON

## 7. Cleanup

- [x] 7.1 Remover `app.py` (Streamlit)
- [x] 7.2 Remover `streamlit` do `pyproject.toml` e rodar `uv sync`
- [x] 7.3 Atualizar `dev.sh` para rodar apenas uvicorn (um processo)
- [x] 7.4 Atualizar `docker-compose.yml` e `Dockerfile` para servir apenas FastAPI
- [x] 7.5 Atualizar `CLAUDE.md` com nova arquitetura de frontend

## 8. Verificação

- [ ] 8.1 Testar chat: enviar pergunta, ver resposta renderizada sem reload
- [ ] 8.2 Testar upload: enviar arquivos .md, ver progress, ver docs na lista
- [ ] 8.3 Testar delete e re-index de documentos
- [ ] 8.4 Testar prompts: editar, salvar, resetar
