## Context

Hoje `caprag/prompts.py` exporta duas funções (`get_rag_prompt`, `get_multi_question_prompt`) que fazem `hub.pull()` contra o LangSmith Hub. Cada chamada é um HTTP request bloqueante. O `ANALYZER_PROMPT` no multi-hop já é uma string local, mostrando que o padrão inline funciona.

O app tem dois usuários (Caio e o GM da campanha). A interface é Streamlit com abas existentes (Chat, Documents).

## Goals / Non-Goals

**Goals:**
- Prompts definidos localmente com defaults no código, sem dependência de rede
- Prompts editáveis via Streamlit e persistidos em disco entre sessões
- Fallback chain: arquivo local em disco > default hardcoded no código
- Interface zero-friction (text area, botão salvar, botão reset)

**Non-Goals:**
- Versionamento de prompts (git já faz isso se o usuário quiser commitar o arquivo)
- Validação de variáveis de template no prompt editado
- Múltiplas versões/A-B testing de prompts
- Separar interface por perfil de usuário

## Decisions

**1. Formato de persistência: arquivo texto puro em `data/prompts/`**

Cada prompt vira um arquivo `.txt` (`data/prompts/rag.txt`, `data/prompts/multi_question.txt`). Texto puro, sem YAML ou JSON wrapping. O conteúdo do arquivo é o template do prompt com placeholders `{variable}`.

Alternativa considerada: YAML com metadata (nome, variáveis, descrição). Descartado porque adiciona parsing sem benefício real para dois prompts numa ferramenta de duas pessoas.

**2. Defaults como `ChatPromptTemplate` no código**

Os prompts default ficam definidos como constantes em `caprag/prompts.py`. Se o arquivo local não existe, a função retorna o default. Isso garante que o sistema sempre funciona mesmo sem nenhum arquivo em `data/prompts/`.

Para obter os defaults atuais, será necessário fazer um pull único do LangSmith Hub (ou copiar o conteúdo dos prompts de lá) antes de remover a dependência.

**3. Carregamento no momento da chamada, não no import**

As funções `get_rag_prompt()` e `get_multi_question_prompt()` leem do disco a cada chamada. Prompts são pequenos (< 1KB), a leitura é negligível, e isso garante que uma edição via UI seja refletida na próxima pergunta sem restart.

**4. UI numa aba "Prompts" no Streamlit**

Uma aba adicional ao lado de Chat e Documents. Para cada prompt: `st.text_area` com o conteúdo atual, botão "Salvar" que grava em `data/prompts/`, botão "Reset" que deleta o arquivo local (voltando ao default). Exibe quais variáveis o prompt precisa conter como referência (não como validação).

## Risks / Trade-offs

**Prompt editado pode quebrar o pipeline se variáveis forem removidas** → Aceitável. Os dois usuários sabem o que estão fazendo. A UI mostra as variáveis esperadas como referência. Pior caso: reset ao default.

**Prompts default precisam ser extraídos do LangSmith Hub antes da remoção** → Fazer um pull manual ou copiar do LangSmith UI durante a implementação. Risco baixo, ação única.

**Arquivo em `data/prompts/` pode ser perdido em rebuild do Docker** → O `docker-compose.yml` já monta `./data` como volume. Verificar que `data/prompts/` está incluído.
