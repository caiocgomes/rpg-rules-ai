# RPG Rules AI

Sistema agêntico de RAG para responder perguntas sobre RPG a partir de livros de regras. Aceita perguntas em português e inglês, expande a query em múltiplas sub-queries, e retorna respostas estruturadas com citações verbatim, fontes e sugestões de termos relacionados.

Atualmente indexado contra livros de GURPS 4e, mas a arquitetura é agnóstica de sistema.

## Quickstart

### Pré-requisitos

- Python 3.11-3.13
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Uma API key da OpenAI

### Setup

```bash
git clone <repo-url> && cd rpg-rules-ai
uv sync
cp .env.example .env
# Edite .env e preencha OPENAI_API_KEY
```

### Rodando

```bash
./dev.sh
```

FastAPI serve a API e o frontend na porta 8100. Ou via Docker:

```bash
docker compose up --build
```

### Testes

```bash
OPENAI_API_KEY=test-key uv run pytest tests/ -v
```

## Arquitetura

Backend e frontend são desacoplados. A JSON API (`/api/`) é o contrato; o frontend Jinja2+HTMX é um consumidor dela.

O pipeline de resposta é um grafo LangGraph com dois nós:

```
retrieve → generate
```

O nó **retrieve** delega para uma `RetrievalStrategy` plugável (selecionada via `RETRIEVAL_STRATEGY` no `.env`):

- **multi-hop** (default): retrieval iterativo com até 3 hops. Expande a query, recupera, analisa se o contexto é suficiente ou se precisa de buscas adicionais. Lida com interações cross-book.
- **multi-question**: expansão em sub-queries com retrieval paralelo em passo único. Mais rápido, mas perde referências cruzadas.

O nó **generate** sintetiza a resposta com citações, fontes e sugestões de "see also".

### Storage

Retrieval usa chunking hierárquico: child chunks para precisão de busca vetorial, parent chunks para contexto na resposta.

- **Vector store**: Chroma com persistência em `./data/chroma`
- **Docstore**: `LocalFileStore` em `./data/docstore/` para parent documents
- **Sources**: markdown em `./data/sources/`

### Frontend

Jinja2 + HTMX servido pelo FastAPI. Três páginas: Chat (`/`), Documents (`/documents`), Prompts (`/prompts/page`). CSS via Pico CSS com overrides mínimos.

## Configuração

Todas as variáveis via `.env` (veja `.env.example`):

| Variável | Obrigatória | Default | Descrição |
|----------|-------------|---------|-----------|
| `OPENAI_API_KEY` | Sim | — | API key da OpenAI |
| `LANGSMITH_API_KEY` | Não | — | Habilita tracing no LangSmith |
| `LANGCHAIN_PROJECT` | Não | `rpg-rules-ai` | Projeto no LangSmith |
| `CHROMA_PERSIST_DIR` | Não | `./data/chroma` | Persistência do vector store |
| `DOCSTORE_DIR` | Não | `./data/docstore` | Persistência do docstore |
| `SOURCES_DIR` | Não | `./data/sources` | Diretório de fontes markdown |
| `LLM_MODEL` | Não | `gpt-4o-mini` | Modelo para geração e expansão |
| `EMBEDDING_MODEL` | Não | `text-embedding-3-large` | Modelo de embeddings |
| `RETRIEVAL_STRATEGY` | Não | `multi-hop` | Estratégia de retrieval |

## Deploy (Linux com systemd)

O script `deploy/install.sh` faz o setup completo numa máquina Linux. Roda como root:

```bash
curl -fsSL https://raw.githubusercontent.com/caiocgomes/rpg-rules-ai/main/deploy/install.sh | sudo bash
```

O que ele faz: instala `uv` se necessário, clona o repo em `/opt/rpg-rules-ai`, cria o virtualenv via `uv sync`, configura o env file em `/etc/rpg-rules-ai/env`, cria o usuário de sistema `rpg-rules-ai`, instala e habilita o serviço systemd. Se `OPENAI_API_KEY` não estiver configurada, o serviço é instalado mas não iniciado.

Para instalar em outro diretório:

```bash
sudo INSTALL_DIR=/srv/rpg-rules-ai bash deploy/install.sh
```

Depois de configurar a API key:

```bash
sudo vim /etc/rpg-rules-ai/env          # preencher OPENAI_API_KEY
sudo systemctl start rpg-rules-ai
```

Para atualizar uma instalação existente, rode o mesmo script novamente. Ele faz `git pull` e `uv sync` sem perder dados ou configuração.

## Estrutura

```
rpg_rules_ai/
├── api.py            # JSON API endpoints (/api/)
├── frontend.py       # Rotas HTMX (/, /documents, /prompts/page)
├── services.py       # Service layer compartilhado
├── graph.py          # Grafo LangGraph (retrieve → generate)
├── schemas.py        # Pydantic models (State, AnswerWithSources, etc.)
├── strategies/       # Estratégias de retrieval plugáveis
│   ├── base.py       # ABC RetrievalStrategy
│   ├── factory.py    # Factory por nome
│   ├── multi_hop.py  # Retrieval iterativo com análise de suficiência
│   └── multi_question.py  # Retrieval paralelo single-pass
├── retriever.py      # Chroma + ParentDocumentRetriever
├── pipeline.py       # Pipeline de ingestão (parse → split → embed → store)
├── ingest.py         # Operações de documento (delete, reindex, metadata)
├── ingestion_job.py  # Job tracking assíncrono
├── prompts.py        # Prompts default + override por arquivo
├── config.py         # Settings (pydantic-settings)
├── templates/        # Jinja2 templates
└── static/           # CSS, JS (htmx)
```
