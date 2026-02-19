## 1. CSS utilities e estrutura base

- [x] 1.1 Adicionar classes `.sr-only` e `.skip-link` em `caprag/static/style.css`
- [x] 1.2 Substituir `<strong>CapaRAG</strong>` no nav de `base.html` por `<h1>` estilizado inline no nav (sem quebrar layout Pico)

## 2. Labels de formulários

- [x] 2.1 Adicionar `<label>` visível para o input de arquivo em `documents.html`
- [x] 2.2 Adicionar `<label>` visível para o input de diretório em `documents.html`
- [x] 2.3 Adicionar `aria-labelledby` no textarea de `prompt_card.html` apontando para o header com nome do prompt (requer `id` no `<strong>`)

## 3. Entity graph dialog nativo

- [x] 3.1 Converter o `<div class="entity-graph-modal">` em `chat_answer.html` para `<dialog>` com `aria-labelledby` no título
- [x] 3.2 Adicionar `aria-label="Close entity graph"` no botão de fechar (`&times;`)
- [x] 3.3 Migrar `openEntityGraph()` em `base.html` para usar `dialog.showModal()` em vez de `style.display = 'block'`
- [x] 3.4 Migrar `closeEntityGraph()` para usar `dialog.close()` com retorno de foco ao botão trigger
- [x] 3.5 Remover handler global `handleEntityGraphKeydown` (Escape é nativo do `<dialog>`)
- [x] 3.6 Adicionar estilos para `<dialog>` e `::backdrop` em `style.css`

## 4. Fallback tabular do entity graph

- [x] 4.1 No `openEntityGraph()`, gerar tabela de entidades (nome, tipo, livro) a partir de `data.nodes` e inserir antes do canvas
- [x] 4.2 Gerar tabela de relações (entidade A, relação, entidade B) resolvendo `from`/`to` dos edges para labels dos nodes
- [x] 4.3 Marcar o `<div class="graph-container">` (canvas) com `aria-hidden="true"`
- [x] 4.4 Tratar caso vazio: mostrar "No entities found for this answer" quando `data.nodes.length === 0`

## 5. Citation links acessíveis

- [x] 5.1 Alterar o regex em `renderAnswer()` de `base.html` para gerar `<a href="#cite-$1" class="cite-marker" aria-label="Citation $1">[$1]</a>`

## 6. Verificação

- [ ] 6.1 Testar com VoiceOver no Safari: navegação por headings, formulários, dialog do entity graph, citações (MANUAL)
- [ ] 6.2 Verificar que a experiência visual não mudou (nenhum elemento novo visível, layout preservado) (MANUAL)
