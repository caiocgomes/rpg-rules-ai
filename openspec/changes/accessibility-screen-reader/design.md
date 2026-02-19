## Context

O frontend do CapaRAG é Jinja2 + HTMX servido pelo FastAPI. Templates em `caprag/templates/`, CSS em `caprag/static/style.css`, JavaScript inline em `base.html`. A base CSS é Pico CSS via CDN, que já fornece estilos acessíveis para elementos nativos (`<button>`, `<input>`, `<dialog>`), mas não fornece classes utilitárias como `.sr-only`.

O entity graph usa vis-network (canvas-based). O endpoint `/api/entity-graph?chunks=...` retorna `{ nodes: [...], edges: [...] }` com campos `id`, `label`, `type`, `entity_type`, `direct`, `relation` etc. Esses dados são suficientes para gerar uma tabela acessível sem tocar no backend.

Já existe: skip link, `aria-live` no chat, `aria-current` na nav, handler de Escape no modal, retorno de foco no close. O trabalho é corrigir lacunas, não reescrever.

## Goals / Non-Goals

**Goals:**
- Operação completa do CapaRAG via screen reader (VoiceOver, NVDA, JAWS) sem pontos onde o usuário fica bloqueado ou sem informação
- Conformidade com WCAG 2.1 Level A nos itens que afetam screen readers
- Manter a experiência visual inalterada para usuários visuais

**Non-Goals:**
- WCAG 2.1 Level AA completo (contraste de cor, redimensionamento de texto, etc. ficam fora deste escopo)
- Acessibilidade de teclado além do que já funciona (tab order está razoável, o foco principal é screen reader)
- Reescrever o entity graph em tecnologia acessível (SVG com ARIA, D3.js etc.). O fallback tabular resolve o acesso à informação sem substituir a visualização

## Decisions

**1. `<dialog>` nativo em vez de `role="dialog"` manual**

O elemento `<dialog>` com `.showModal()` fornece focus trap, stacking context, Escape handler e `aria-modal` automaticamente. Alternativa seria manter o `<div>` atual e adicionar focus trap manual em JS + `role="dialog"` + `aria-modal="true"`. O `<dialog>` nativo reduz código e bugs; suporte em browsers é universal desde 2022. Escolha: `<dialog>`.

Consequência: o handler de Escape e o retorno de foco que já existem em `base.html` podem ser simplificados. O `<dialog>` dispara evento `close` que substitui o listener global de keydown.

**2. Fallback tabular dentro do `<dialog>`, antes do canvas**

A tabela de entidades aparece dentro do mesmo `<dialog>` do grafo, acima do canvas. Para screen readers, a tabela é o conteúdo; para usuários visuais, o grafo visual continua dominante. O canvas recebe `aria-hidden="true"`.

A tabela é gerada pelo mesmo `fetch` que alimenta o vis.js. O JSON já tem a estrutura necessária: cada node tem `label` e `entity_type`, cada edge tem `from`, `to`, `relation`. A tabela lista entidades (nome, tipo, livro) e relações (entidade A → relação → entidade B).

Alternativa considerada: tabela separada fora do modal, acessível por outro botão. Descartada porque duplica a interação e fragmenta o fluxo.

**3. `aria-label` nos cite links via regex no JavaScript**

O regex atual em `base.html:24` que transforma `[N]` em `<a>` será estendido para incluir `aria-label="Citation N"`. Mudança de uma linha no regex. Alternativa seria usar `role="doc-noteref"` (especificação DPUB-ARIA), que é semanticamente mais rico mas tem suporte inconsistente em screen readers. `aria-label` é universalmente suportado.

**4. `<h1>` no base template, não por página**

O `<h1>` será "CapaRAG" no `base.html`, visualmente integrado ao nav (substituindo o `<strong>` atual). Cada página mantém `<h2>` como título de seção. Alternativa: `<h1>` diferente por página (Chat, Documents, Prompts). Descartada porque o site é single-purpose, "CapaRAG" identifica o produto, e o `<h2>` por página já diferencia as seções.

**5. Labels visíveis para os formulários sem label**

Para o file input e o directory input em `documents.html`, adicionar `<label>` visíveis acima dos campos. Para o textarea em `prompt_card.html`, usar `aria-labelledby` apontando para o header que já contém o nome do prompt. Labels visíveis são preferíveis a `aria-label` porque beneficiam todos os usuários (Fitts' law: área clicável maior).

## Risks / Trade-offs

**`<dialog>` pode conflitar com estilos Pico CSS** → Pico CSS estiliza `<dialog>` nativamente desde v2. Testar se o backdrop e padding precisam de override no `style.css`. Risco baixo.

**Tabela de fallback aumenta o DOM do chat** → Cada resposta com entity graph terá uma tabela extra dentro do `<dialog>`. Como o dialog só é populado on-demand (no click do botão), não afeta o carregamento inicial. O conteúdo é limpo quando o dialog fecha.

**vis-network com `aria-hidden="true"` esconde tooltips** → O vis.js tem tooltips nativos nos nós, que já não são acessíveis (canvas). Sem impacto adicional.
