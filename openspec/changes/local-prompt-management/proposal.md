## Why

Os prompts do sistema são carregados em runtime via `langchain hub.pull()`, o que cria dependência de rede com o LangSmith Hub em cada execução. Isso adiciona latência, introduz um ponto de falha externo (qualquer mudança na API do LangSmith quebra o sistema), e impede iteração rápida nos prompts sem commit. Para um app usado por duas pessoas onde a qualidade da resposta depende diretamente do prompt, poder editar e testar na mesma sessão é mais valioso do que versionamento remoto.

## What Changes

- **BREAKING**: Remover dependência do `langchain hub.pull()` para carregamento de prompts
- Definir prompts default no código como `ChatPromptTemplate`
- Persistir prompts editados em arquivos locais (`data/prompts/`)
- Adicionar aba no Streamlit para visualizar e editar os prompts ativos
- Carregar prompts com fallback: arquivo local > default no código

## Capabilities

### New Capabilities
- `prompt-management`: Gerenciamento local de prompts com persistência em arquivo e edição via UI

### Modified Capabilities
- `web-interface`: Adicionar aba/seção de edição de prompts na interface Streamlit

## Impact

- `caprag/prompts.py`: reescrever para carregar de arquivo local com fallback para defaults
- `caprag/graph.py`: sem mudança de interface (continua chamando `get_rag_prompt()`)
- `caprag/strategies/multi_hop.py` e `multi_question.py`: sem mudança de interface
- `app.py`: adicionar UI de edição de prompts
- Remover import de `langchain_classic.hub`
- Diretório `data/prompts/` para persistência
