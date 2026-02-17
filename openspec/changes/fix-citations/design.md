## Context

O nó `generate` em `graph.py` recebe documentos recuperados pelo multi-hop, concatena seus conteúdos num bloco de texto e envia ao LLM com structured output (`AnswerWithSources`). O schema define `citations: List[Citation]` onde cada `Citation` tem `quote` (trecho verbatim) e `source` (nome do livro). Na prática, o LLM preenche `sources` mas retorna `citations` vazio ou genérico, porque nada no prompt exige o preenchimento e o contexto injetado não facilita extração.

Dois arquivos concentram o problema: `caprag/prompts.py` (template do prompt) e `caprag/graph.py` (formatação do contexto na função `generate`).

## Goals / Non-Goals

**Goals:**
- Citations preenchidas com quotes verbatim extraídas do contexto para cada afirmação factual da resposta
- Contexto formatado de modo que o LLM consiga localizar e copiar trechos específicos

**Non-Goals:**
- Refatorar a atribuição de docs no multi-hop (`questions[0].context = all_docs`). Isso fica como trabalho futuro.
- Validação pós-resposta (rejeitar respostas com citations vazias). Pode ser feito depois se o prompt não resolver.
- Alterar o schema `Citation` ou `AnswerWithSources`.

## Decisions

**1. Prompt com instrução explícita de citations**

O `DEFAULT_RAG_TEMPLATE` passa a incluir instrução de que toda afirmação factual precisa de uma citation com o trecho exato copiado do contexto. Alternativa considerada: adicionar `minItems` no JSON schema do structured output. Descartada porque o controle via prompt é mais flexível e não depende de suporte do provider ao campo `minItems`.

**2. Contexto numerado com separadores**

Cada documento no contexto recebe um índice (`[1]`, `[2]`, ...) e separador visual (`---`). O formato fica:

```
[1] Source: GURPS Basic Set
{page_content}
---
[2] Source: GURPS Martial Arts
{page_content}
---
```

Alternativa considerada: usar XML tags (`<doc id="1">...</doc>`). Funciona bem com alguns modelos mas adiciona tokens sem ganho claro sobre separadores simples. A numeração sequencial já dá "handles" suficientes para o LLM referenciar trechos.

**3. Manter o limite de 3 sentenças mas ajustar para acomodar citations**

O prompt atual diz "Use three sentences maximum". Isso pode conflitar com a exigência de citations detalhadas. O novo prompt mantém a instrução de concisão mas reformula para não criar tensão com o preenchimento de citations (as citations vivem no campo structured, não no corpo da resposta).

## Risks / Trade-offs

**Aumento de tokens de saída** → O LLM vai gerar mais texto no campo citations. Para parent chunks de 2000 chars, cada quote pode ter centenas de chars. Impacto em custo e latência é proporcional ao número de citations. Mitigação: o prompt pede citations para afirmações factuais, não para cada frase.

**Quotes não-verbatim** → Mesmo com instrução explícita, LLMs às vezes parafraseiam em vez de copiar. Mitigação: a numeração do contexto facilita a cópia exata. Se persistir, validação pós-resposta pode ser adicionada depois.

**Testes existentes** → Testes que mocam o prompt ou verificam o formato do contexto vão quebrar. Impacto pequeno e previsível.
