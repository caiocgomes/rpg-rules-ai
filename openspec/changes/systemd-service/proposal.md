## Why

Hoje o CapaRAG só roda via `./dev.sh` (foreground com --reload) ou Docker. Em servidor Linux compartilhado, precisa rodar como serviço systemd: start/stop/restart via `systemctl`, auto-restart em crash, boot automático, logs no journald, e isolamento de permissões. Sem isso, o processo morre quando o terminal fecha ou o servidor reinicia.

## What Changes

- Criar unit file systemd (`caprag.service`) que executa uvicorn diretamente via uv
- Criar script de instalação que copia o unit file, cria usuário de serviço, configura diretórios e habilita o serviço
- Adicionar EnvironmentFile para carregar `.env` como configuração do serviço
- Documentar deploy em Linux no README ou em doc separada

## Capabilities

### New Capabilities
- `systemd-deploy`: unit file systemd, script de instalação, configuração de deploy para servidor Linux compartilhado

### Modified Capabilities
(nenhuma)

## Impact

- **Novos arquivos**: `deploy/caprag.service`, `deploy/install.sh`
- **Configuração**: `.env` passa a ser o EnvironmentFile do systemd (já é o padrão do projeto)
- **Permissões**: precisa de usuário dedicado com acesso ao diretório de dados (`./data/`)
- **Dependências do sistema**: Python 3.11+, uv, systemd
- **Backend/API**: sem mudanças
