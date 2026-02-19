## 1. Unit file systemd

- [x] 1.1 Criar `deploy/caprag.service` com ExecStart via `uv run uvicorn`, EnvironmentFile, User=caprag, Restart=on-failure, RestartSec=5, StartLimitBurst=3
- [x] 1.2 Parametrizar porta (`$PORT` default 8100) e workers (`$WORKERS` default 1) no ExecStart

## 2. Script de instalação

- [x] 2.1 Criar `deploy/install.sh` com verificação de root e presença de uv
- [x] 2.2 Criar usuário `caprag` (system, nologin) se não existir
- [x] 2.3 Criar diretórios de dados e ajustar permissões (owner caprag)
- [x] 2.4 Gerar o unit file com WorkingDirectory correto (parametrizado por INSTALL_DIR) e copiar para /etc/systemd/system/
- [x] 2.5 Executar daemon-reload e exibir instruções de uso (enable, start, status, logs)

## 3. Configuração

- [x] 3.1 Adicionar `PORT=8100` e `WORKERS=1` ao `.env.example` com comentários

## 4. Verificação

- [x] 4.1 Validar sintaxe do unit file com `systemd-analyze verify` (se disponível no ambiente de teste)
- [x] 4.2 Garantir que install.sh é executável e tem shebang correto
