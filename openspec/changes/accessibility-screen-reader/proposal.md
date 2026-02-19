## Why

O segundo usuário principal do CapaRAG é cego e usa leitor de tela. A interface atual tem falhas que bloqueiam ou degradam a operação via assistive technology: formulários sem labels programáticas (campos invisíveis para o screen reader), modal sem semântica de dialog (foco escapa, screen reader não anuncia abertura), grafo de entidades renderizado em canvas (conteúdo inexistente para leitores de tela), e hierarquia de headings quebrada (navegação por atalhos não funciona).

## What Changes

- Adicionar labels acessíveis (`<label>` ou `aria-labelledby`) nos três formulários que hoje não têm: upload de arquivo, input de diretório, textarea de prompts
- Adicionar `<h1>` em todas as páginas (provavelmente "CapaRAG" no base template ou título da página)
- Substituir o modal do entity graph por `<dialog>` nativo (inclui focus trap e Escape grátis, já tem handler de Escape e retorno de foco implementados)
- Adicionar `aria-label="Close entity graph"` no botão de fechar que hoje usa `&times;`
- Criar fallback tabular dos dados do entity graph dentro do `<dialog>`, acessível via screen reader, como alternativa ao canvas do vis.js
- Adicionar `aria-label` nos links de citação `[N]` gerados pelo regex no JavaScript (hoje lidos como "left bracket, one, right bracket")
- Definir classes CSS utilitárias `.sr-only` e `.skip-link` que são referenciadas nos templates mas não existem no stylesheet

## Capabilities

### New Capabilities
- `a11y`: requisitos de acessibilidade para operação completa via leitor de tela, cobrindo semântica HTML, labels de formulários, landmarks, headings, dialogs modais, e alternativas textuais para conteúdo visual

### Modified Capabilities
- `web-interface`: adicionar requisitos de estrutura semântica (h1, labels, dialog) e alternativa acessível ao entity graph

## Impact

- **Templates**: `base.html`, `chat.html`, `documents.html`, `fragments/chat_answer.html`, `fragments/prompt_card.html`
- **CSS**: `static/style.css` (classes `.sr-only`, `.skip-link`, estilos do `<dialog>`, estilos da tabela de fallback do grafo)
- **JavaScript**: `base.html` inline scripts (migrar modal para `<dialog>`, gerar tabela de fallback a partir dos dados da API, adicionar `aria-label` nos cite links)
- **API**: endpoint `/api/entity-graph` já retorna os dados estruturados (nodes/edges); o fallback tabular consome os mesmos dados, sem mudança no backend
- **Dependências**: nenhuma nova
