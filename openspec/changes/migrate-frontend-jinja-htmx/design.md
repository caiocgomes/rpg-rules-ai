## Context

O CapaRAG usa Streamlit (`app.py`) como frontend, que se comunica com um backend FastAPI (`caprag/api.py`) via HTTP. São dois processos separados em portas diferentes (8100 para API, 8501 para Streamlit). O Streamlit faz chamadas `httpx` ao FastAPI para todas as operações. Essa arquitetura funcionou como protótipo, mas limita o controle sobre o HTML renderizado, impedindo funcionalidades como citações inline com popover.

O FastAPI já expõe todos os endpoints necessários (ask, documents CRUD, upload, jobs, prompts). O frontend é puramente um consumidor desses endpoints. A migração consiste em fazer o FastAPI servir HTML diretamente via Jinja2 templates, usando HTMX para interatividade.

## Goals / Non-Goals

**Goals:**
- Replicar 100% da funcionalidade atual do Streamlit (chat, upload, listagem de docs, progress, prompts)
- Servir tudo a partir de um único processo FastAPI
- Dar controle total sobre o HTML para preparar citações inline (mudança futura)
- Zero build pipeline no frontend (sem Node, npm, webpack)

**Non-Goals:**
- Citações inline (escopo de outra change)
- Streaming token a token da resposta (pode ser adicionado depois)
- Autenticação ou multi-tenancy
- Testes E2E com browser automation (funcionalidade testada via API + template rendering)

## Decisions

### Templates Jinja2 com herança de base template

Estrutura de diretórios:

```
caprag/
  templates/
    base.html        # nav, head (CSS/HTMX includes), block content
    chat.html         # extends base, chat UI
    documents.html    # extends base, upload + list
    prompts.html      # extends base, prompt editors
    fragments/        # parciais retornados por HTMX
      chat_message.html
      chat_answer.html
      doc_list.html
      doc_row.html
      progress.html
      prompt_card.html
  static/
    style.css         # overrides mínimos se necessário
```

Templates completos (chat.html, documents.html, prompts.html) são servidos por rotas GET que retornam `TemplateResponse`. Fragments (parciais) são retornados por rotas HTMX que respondem a interações assíncronas.

Alternativa considerada: templates tudo inline em Python (FastHTML). Descartado porque a separação HTML/Python facilita a manutenção e o Jinja2 é o padrão do ecossistema FastAPI.

### HTMX para interatividade, sem JavaScript customizado

HTMX é carregado via CDN (`<script src="https://unpkg.com/htmx.org@2.x"></script>`). As interações usam atributos HTML:

- `hx-post="/chat/ask"` para enviar perguntas
- `hx-get="/documents/list"` para recarregar a lista de docs
- `hx-delete="/documents/{book}"` para deletar
- `hx-trigger="every 1s"` para polling de progresso
- `hx-swap="beforeend"` / `hx-swap="innerHTML"` conforme necessidade

Alternativa considerada: WebSockets para chat. Descartado por complexidade desnecessária neste momento. Polling via HTMX com SSE como upgrade futuro.

### Rotas HTML separadas das rotas API

As rotas que servem páginas HTML ficam num router separado (`caprag/frontend.py`) montado no mesmo app FastAPI. As rotas JSON da API continuam em `caprag/api.py` inalteradas. As rotas de frontend consomem as mesmas funções internas (get_books_metadata, delete_book, etc.).

```
GET /              → chat.html (página completa)
GET /documents     → documents.html (página completa)
GET /prompts       → prompts.html (página completa)
POST /chat/ask     → fragment chat_answer.html (HTMX)
GET /documents/list → fragment doc_list.html (HTMX)
DELETE /documents/htmx/{book} → fragment vazio + HX-Trigger (HTMX)
POST /documents/htmx/upload → fragment progress.html (HTMX)
GET /documents/htmx/progress/{job_id} → fragment progress.html (HTMX)
GET /prompts/htmx/{name} → fragment prompt_card.html (HTMX)
PUT /prompts/htmx/{name} → fragment prompt_card.html (HTMX)
DELETE /prompts/htmx/{name} → fragment prompt_card.html (HTMX)
```

Alternativa considerada: reescrever as rotas API para aceitar tanto JSON quanto HTML (content negotiation via Accept header). Descartado por adicionar complexidade nas rotas existentes. Melhor manter as rotas JSON intactas e criar rotas HTMX separadas.

### Pico CSS via CDN como framework CSS

Pico CSS é classless (estiliza elementos semânticos sem classes), carregado via CDN. Cobre layout, tipografia, formulários, tabelas. Overrides mínimos em `style.css` para customizações específicas (layout do chat, progress bar).

Alternativa considerada: Tailwind CSS. Descartado por requerer build pipeline (PostCSS). Bootstrap descartado por ser class-heavy.

### Chat com histórico em session (cookie)

O Streamlit mantém histórico de mensagens via `st.session_state` (in-memory, por sessão websocket). No novo frontend, o histórico de mensagens fica no HTML da própria página. Quando o usuário envia uma pergunta, HTMX faz POST com o texto e a resposta é inserida (`hx-swap="beforeend"`) no container de mensagens. Ao navegar para outra página e voltar, o histórico se perde (acceptable nesta fase).

Alternativa considerada: persistir histórico server-side com session cookie. Descartado por adicionar complexidade sem benefício claro neste momento. O chat do CapaRAG é stateless por natureza (cada pergunta é independente).

## Risks / Trade-offs

[Sem polling nativo de longa duração] O polling de progresso via `hx-trigger="every 1s"` gera requests frequentes. Para jobs curtos não é problema. Para jobs longos com muitos arquivos, pode gerar carga. → Mitigação: intervalo de 2s, stop polling quando status="done" ou "error".

[Perda de histórico de chat ao navegar] Sem session server-side, trocar de página perde o chat. → Mitigação: aceitar como limitação V1. Se necessário depois, usar `hx-boost` para navegação SPA-like que preserva o DOM.

[HTMX como dependência CDN] Se o CDN cair, a interface quebra. → Mitigação: baixar htmx.min.js para `caprag/static/` e servir localmente. Mesmo com Pico CSS.

## Open Questions

Nenhuma no momento. Decisões de streaming e citações inline ficam para changes futuras.
