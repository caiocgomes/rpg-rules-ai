## Context

O `generate` node monta contexto numerado `[1] Source: book\ncontent` e o LLM preenche `AnswerWithSources` via structured output. Hoje o `answer` é texto puro e `citations` é lista desconectada. O frontend renderiza citations num `<details>` colapsável.

## Goals / Non-Goals

**Goals:**
- Cada afirmação no texto tem marcador `[N]` que referencia uma citation específica
- Citations renderizadas como blocos visíveis abaixo do texto, na ordem de referência
- Click no `[N]` scrolla/destaca o bloco correspondente
- Quote verbatim preserva a língua original do trecho fonte

**Non-Goals:**
- Tooltip/popover ao hover (complexidade JS desproporcional, blocos visíveis são suficientes)
- Edição de citations pelo usuário
- Múltiplas citations por marcador na v1 (tipo `[1,3]`)

## Decisions

### 1. Schema: Citation com index

```python
class Citation(TypedDict):
    index: int    # 1-based, corresponde ao [N] no texto
    quote: str    # verbatim do contexto
    source: str   # nome do livro

class AnswerWithSources(TypedDict):
    answer: str              # "Texto com [1] marcadores [2] inline."
    citations: List[Citation]
    sources: List[str]
    see_also: List[str]
```

O campo `index` é redundante com a posição na lista mas explícito para o LLM e para validação. O LLM recebe instrução de preencher `index` matching os `[N]` no texto.

### 2. Prompt com instrução explícita

O prompt instrui:
- Inserir `[N]` no texto do answer após cada afirmação factual
- Cada `[N]` deve corresponder a uma citation com `index: N`
- O `quote` deve ser copiado VERBATIM do contexto numerado
- O `source` deve ser o nome do livro exatamente como aparece após "Source:"
- Manter língua original do trecho fonte na quote

O contexto já chega numerado (`[1] Source: GURPS Basic Set\n...`), então o LLM tem referências claras para usar.

### 3. Validação pós-LLM

Após receber a resposta do LLM, o backend valida:
1. Extrai todos os `[N]` do texto via regex `\[(\d+)\]`
2. Filtra citations cujo `index` não aparece no texto (citations órfãs)
3. Filtra marcadores no texto que não têm citation correspondente (remove do texto)
4. Renumera sequencialmente se houver gaps (não estritamente necessário na v1, mas limpa)

Isso garante que o frontend nunca recebe um `[3]` sem citation 3 ou vice-versa.

### 4. Frontend: blocos de referência

O template `chat_answer.html` muda de:
- `<div>{{ answer.answer }}</div>` + `<details>` com citations

Para:
- `<div>` com answer processado: `[N]` vira `<a href="#cite-N" class="cite-marker">[N]</a>`
- Blocos de citation visíveis abaixo do texto:
```html
<div class="citations-block">
  <div class="citation-ref" id="cite-1">
    <span class="cite-index">[1]</span>
    <span class="cite-source">GURPS Basic Set</span>
    <blockquote>verbatim quote here</blockquote>
  </div>
  ...
</div>
```

Click no `[N]` no texto faz scroll suave até o `#cite-N`. O bloco referenciado recebe highlight temporário via CSS (`:target` pseudo-class ou JS mínimo).

### 5. CSS

- `.cite-marker`: estilo de link discreto (cor accent, sem underline, superscript opcional)
- `.citation-ref`: borda esquerda colorida, padding, fundo levemente diferente
- `.citation-ref:target`: highlight temporário (background flash)
- `.cite-source`: bold, cor secundária
- `blockquote` dentro de citation: italic, recuo

## Risks / Trade-offs

**[LLM pode não gerar marcadores consistentes]** → Mitigado pela validação pós-LLM. Worst case: resposta sem marcadores, citations viram lista simples como hoje (graceful degradation).

**[Structured output com `[N]` no texto pode confundir o parser]** → `with_structured_output()` do LangChain pede JSON. O `[N]` dentro de uma string JSON é safe (não conflita com JSON syntax). Testado: GPT-4o-mini e GPT-4o geram `[1]` dentro de strings JSON sem problema.

**[Respostas ficam mais verbosas com marcadores]** → O prompt já limita a 3 frases. Os marcadores adicionam ~4 chars cada. Impacto negligível.
