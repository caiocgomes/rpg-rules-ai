## ADDED Requirements

### Requirement: systemd unit file
O projeto SHALL incluir um unit file systemd em `deploy/caprag.service` que executa o CapaRAG como serviço.

#### Scenario: Iniciar serviço
- **WHEN** o administrador executa `systemctl start caprag`
- **THEN** o uvicorn inicia no host e porta configurados, servindo a API e o frontend

#### Scenario: Parar serviço
- **WHEN** o administrador executa `systemctl stop caprag`
- **THEN** o processo uvicorn recebe SIGTERM e encerra gracefully

#### Scenario: Auto-restart em crash
- **WHEN** o processo uvicorn termina inesperadamente
- **THEN** o systemd reinicia o serviço após 5 segundos, com limite de 3 tentativas em 30 segundos

#### Scenario: Start no boot
- **WHEN** o administrador executa `systemctl enable caprag` e o servidor reinicia
- **THEN** o serviço inicia automaticamente durante o boot

#### Scenario: Logs no journald
- **WHEN** o administrador executa `journalctl -u caprag`
- **THEN** os logs do uvicorn (stdout + stderr) são exibidos com timestamps

### Requirement: Configuração via EnvironmentFile
O unit file SHALL carregar variáveis de ambiente de um arquivo `.env` via diretiva `EnvironmentFile`.

#### Scenario: Variáveis de ambiente carregadas
- **WHEN** o serviço inicia
- **THEN** todas as variáveis definidas no `.env` (OPENAI_API_KEY, LLM_MODEL, CHROMA_PERSIST_DIR, etc.) estão disponíveis para o processo

#### Scenario: Porta configurável
- **WHEN** o `.env` contém `PORT=9000`
- **THEN** o uvicorn escuta na porta 9000

#### Scenario: Workers configurável
- **WHEN** o `.env` contém `WORKERS=4`
- **THEN** o uvicorn inicia com 4 worker processes

### Requirement: Script de instalação
O projeto SHALL incluir um script `deploy/install.sh` que configura o serviço systemd.

#### Scenario: Instalação completa
- **WHEN** o administrador executa `sudo deploy/install.sh`
- **THEN** o script cria o usuário `caprag`, copia o unit file para `/etc/systemd/system/`, cria diretórios de dados com permissões corretas, executa `systemctl daemon-reload`, e exibe instruções para habilitar e iniciar o serviço

#### Scenario: Diretório de instalação customizado
- **WHEN** o administrador executa `sudo INSTALL_DIR=/srv/caprag deploy/install.sh`
- **THEN** o unit file aponta WorkingDirectory para `/srv/caprag`

#### Scenario: Execução sem root
- **WHEN** o script é executado sem sudo
- **THEN** o script exibe uma mensagem de erro e termina com exit code 1

#### Scenario: uv não instalado
- **WHEN** o script é executado e `uv` não está no PATH
- **THEN** o script exibe um aviso com instruções de instalação do uv e termina com exit code 1

### Requirement: Variáveis PORT e WORKERS no .env.example
O `.env.example` SHALL incluir `PORT` e `WORKERS` como variáveis opcionais com defaults documentados.

#### Scenario: Defaults documentados
- **WHEN** o administrador consulta `.env.example`
- **THEN** encontra `PORT=8100` e `WORKERS=1` com comentários explicativos
