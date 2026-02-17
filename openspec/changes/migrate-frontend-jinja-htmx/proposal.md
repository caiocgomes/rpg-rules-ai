## Why

O Streamlit funciona bem como protótipo, mas impõe limites concretos no controle de renderização. O próximo passo do CapaRAG exige citações inline com popover interativo (clique num marcador `[1]` e veja o trecho original). Streamlit não suporta isso sem injetar HTML/JS customizado via `st.components`, o que resulta em gambiarras frágeis que quebram a cada atualização do framework. Migrar o frontend para Jinja2 templates servidos pelo FastAPI existente, com HTMX para interatividade, dá controle total sobre o HTML sem introduzir um segundo ecossistema (Node/React) e sem build step.

## What Changes

- Substituir `app.py` (Streamlit) por templates Jinja2 servidos pelo FastAPI em `caprag/api.py`
- Adicionar rotas HTML no FastAPI que servem as mesmas três páginas (Chat, Documents, Prompts)
- Usar HTMX para interações assíncronas: envio de perguntas, polling de progresso de ingestão, delete/re-index de documentos, edição de prompts
- Chat usa Server-Sent Events (SSE) ou HTMX polling para exibir a resposta sem reload completo
- CSS mínimo (pode ser Pico CSS ou similar classless framework) para não precisar de pipeline de build
- **BREAKING**: `app.py` (Streamlit) será removido. O comando de dev muda de `streamlit run app.py` para apenas o uvicorn servindo tudo
- `dev.sh` e `docker-compose.yml` simplificam para um único processo

## Capabilities

### New Capabilities
- `jinja-frontend`: Templates Jinja2 + HTMX que replicam as três tabs atuais (chat, documents, prompts) com controle total sobre o HTML renderizado

### Modified Capabilities
- `web-interface`: Os requisitos funcionais permanecem os mesmos (upload, listagem, delete, re-index, progress, chat), mas a tecnologia de implementação muda de Streamlit para Jinja2+HTMX. Os cenários de teste precisam ser adaptados para o novo stack.

## Impact

- **Código removido**: `app.py` (Streamlit frontend inteiro)
- **Código novo**: templates em `caprag/templates/`, rotas HTML em `caprag/api.py` (ou router separado)
- **Dependências**: adicionar `jinja2`, `python-multipart` (já existe), `htmx` (CDN, sem pacote Python). Remover `streamlit` do `pyproject.toml`
- **Infra**: `dev.sh` e `docker-compose.yml` simplificam de dois processos para um. O Dockerfile não precisa mais expor duas portas
- **Testes**: testes de API existentes continuam válidos. Testes de frontend (se houver) precisam ser reescritos
- **Usuário**: a URL muda de `localhost:8501` para `localhost:8100` (já é onde o FastAPI roda)
