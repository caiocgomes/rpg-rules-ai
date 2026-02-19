## Context

O CapaRAG é um FastAPI app que roda com `uv run uvicorn caprag.api:app --host 0.0.0.0 --port 8100`. Configuração via `.env` (pydantic-settings). Dados persistidos em `./data/` (chroma, docstore, entity index, prompts, sources). O servidor é compartilhado, então porta, paths e usuário precisam ser configuráveis.

## Goals / Non-Goals

**Goals:**
- `systemctl start caprag` / `systemctl stop caprag` / `systemctl restart caprag`
- Auto-restart em crash (com backoff)
- Start no boot (`systemctl enable caprag`)
- Logs acessíveis via `journalctl -u caprag`
- Script de instalação que configura tudo de uma vez
- Configurável para servidor compartilhado (porta, diretório de instalação, usuário)

**Non-Goals:**
- Múltiplas instâncias no mesmo servidor
- Proxy reverso (nginx/caddy) — o usuário configura separadamente
- SSL/TLS — fica no proxy reverso
- Logrotate customizado — journald já faz rotação

## Decisions

**1. Execução via uv, não via venv direto**

O projeto usa uv e não tem `requirements.txt`. O unit file chama `uv run uvicorn` diretamente, igual ao `dev.sh` mas sem `--reload`. Alternativa seria gerar um venv com `uv sync` e chamar o uvicorn do venv. O `uv run` é mais simples e mantém consistência com o workflow do projeto.

**2. EnvironmentFile em vez de variáveis inline no unit**

O systemd suporta `EnvironmentFile=/path/to/.env`, que é exatamente o formato que o projeto já usa. Sem duplicar configuração. O `.env` fica no diretório de instalação, permissão 600 (contém API keys).

**3. Usuário de serviço dedicado**

O script cria um usuário `caprag` (nologin, sem home) owner dos diretórios de dados. Alternativa seria rodar como root (inseguro) ou como o usuário atual (frágil em servidor compartilhado). O usuário dedicado isola permissões e segue a convenção systemd.

**4. Diretório de instalação parametrizado**

Default: `/opt/caprag`. O script de instalação aceita `INSTALL_DIR` como override. O unit file usa `WorkingDirectory` apontando para o install dir. Alternativa seria hardcodar `/opt/caprag`, mas servidor compartilhado pode ter convenções diferentes.

**5. Porta configurável via .env**

Adicionar `PORT=8100` ao `.env.example`. O unit file passa `--port $PORT` ao uvicorn, lendo da variável de ambiente. O `config.py` não precisa mudar — a porta é parâmetro do uvicorn, não do app.

**6. Workers configurável**

Adicionar `WORKERS=1` ao `.env.example`. Em produção com múltiplos cores, o usuário pode escalar. O unit file passa `--workers $WORKERS` ao uvicorn.

## Risks / Trade-offs

**uv precisa estar instalado system-wide** → O script de instalação verifica se `uv` existe e sugere instalação se não encontrar. Não instala automaticamente para evitar surpresas em servidor compartilhado.

**`uv run` faz sync a cada start** → Na prática o sync é no-op se `uv.lock` não mudou. Custo desprezível no startup. Se incomodar, pode trocar para `uv sync && .venv/bin/uvicorn` no ExecStart.

**Atualização do app requer restart manual** → O unit file não monitora mudanças no código. Workflow: `git pull && uv sync && systemctl restart caprag`. O script de instalação pode incluir um helper para isso.
