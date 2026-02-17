## Context

O CapaRAG serve uma JSON API (`/api/`) e um frontend HTMX a partir do mesmo processo FastAPI. Ambos os módulos (`api.py` e `frontend.py`) mantêm singletons independentes de `_graph` e `_jobs`, importam diretamente `build_graph`, `IngestionJob`, funções de `ingest` e `prompts`, e reimplementam lógica de orquestração (criação de job, validação de arquivo, construção de respostas de prompt). Isso gera dois graphs em memória e dois registries de jobs isolados: um job criado via HTMX não aparece via `/api/documents/jobs/{id}` e vice-versa.

O CLAUDE.md define que a JSON API é o contrato e o frontend é apenas um consumidor, mas o código viola isso porque ambos os routers contêm lógica de negócio idêntica.

## Goals / Non-Goals

**Goals:**

- Eliminar duplicação de singletons e lógica de orquestração entre `api.py` e `frontend.py`
- Garantir que existe exatamente um graph e um job registry por processo
- Fazer com que ambos os routers sejam wrappers finos: `api.py` traduz para JSON, `frontend.py` traduz para HTML/HTMX
- Preservar 100% dos endpoints existentes (URLs, métodos HTTP, formatos de resposta)

**Non-Goals:**

- Alterar a interface pública da JSON API (request/response schemas)
- Modificar templates HTMX ou CSS
- Refatorar `IngestionJob`, `pipeline.py`, `graph.py` ou `prompts.py`
- Adicionar testes novos neste change (os testes existentes devem continuar passando)
- Introduzir dependency injection framework ou abstrações além do service module

## Decisions

**Service module como namespace de funções stateful, não classe.**
O `caprag/services.py` expõe funções (`ask_question`, `create_ingestion_job`, `get_job_progress`, `list_books`, `delete_book`, `list_prompts`, `get_prompt`, `save_prompt`, `reset_prompt`) que encapsulam acesso aos singletons internos (`_graph`, `_jobs`). Os singletons ficam privados ao módulo. Alternativa considerada: uma classe `ServiceLayer` instanciada como singleton via `@lru_cache` ou dependency injection do FastAPI (`Depends`). Descartada porque adiciona indireção sem benefício, o processo já é single-instance, e funções simples são mais fáceis de testar com mock.

**Validação de domínio no service layer como exceções Python.**
Validações como "arquivo deve ser .md", "path deve existir", "prompt name deve ser válido" lançam exceções Python padrão (`ValueError`, `FileNotFoundError`, `KeyError`). Cada router traduz para seu formato: `api.py` converte em `HTTPException` com status code adequado, `frontend.py` converte em `HTMLResponse` com mensagem de erro. Alternativa: validação duplicada em cada router (status quo). Descartada porque é exatamente o problema que estamos resolvendo.

**Upload de arquivo permanece nos routers.**
O recebimento de `UploadFile` e gravação em disco é responsabilidade do router porque `UploadFile` é conceito FastAPI/HTTP. O service recebe `list[Path]` já salvas. Isso mantém o service layer agnóstico ao framework web.

**Nenhum re-export de `_graph` ou `_jobs`.**
Os singletons não são expostos diretamente. Acesso ao graph é via `ask_question()`, acesso a jobs é via `create_ingestion_job()` / `get_job_progress()`. Isso permite trocar a implementação interna sem quebrar consumidores.

## Risks / Trade-offs

Importações circulares entre `services.py` e outros módulos (`graph.py`, `ingest.py`) → Mitigação: `services.py` importa de `graph`, `ingest`, `prompts` e `ingestion_job`, nunca o inverso. Os routers importam apenas de `services`. O lazy import de `build_graph` (já existente no padrão `_get_graph`) se mantém no service.

Mudança de módulo dos singletons pode causar problemas se algum código externo importar `_graph` de `api.py` ou `frontend.py` → Mitigação: esses singletons são prefixados com `_` (privados por convenção). Nenhum outro módulo os importa. Testes que mockem `api._graph` precisarão apontar para `services._graph` ou (preferível) mockar `services.ask_question`.

Risco de regressão em endpoints HTMX cujo comportamento depende de side effects sutis → Mitigação: testar manualmente os três fluxos (chat, upload+progress, prompts save/reset) após a migração. Os testes unitários existentes cobrem o service layer indiretamente.
