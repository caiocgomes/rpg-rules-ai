## ADDED Requirements

### Requirement: Citations verbatim obrigatórias

O sistema SHALL incluir no campo `citations` da resposta ao menos uma `Citation` para cada afirmação factual presente no campo `answer`. Cada `Citation` SHALL conter o trecho exato (verbatim) copiado do contexto no campo `quote` e o nome do livro de origem no campo `source`.

#### Scenario: Resposta com múltiplas afirmações de um mesmo livro
- **WHEN** o usuário pergunta sobre uma regra coberta por múltiplos trechos do mesmo livro
- **THEN** a resposta contém uma citation separada para cada afirmação factual, todas com o mesmo `source` mas `quote` distintos

#### Scenario: Resposta com afirmações de livros diferentes
- **WHEN** o usuário pergunta sobre uma regra que envolve cross-references entre livros
- **THEN** a resposta contém citations com `source` apontando para cada livro utilizado, e cada `quote` é um trecho verbatim do respectivo livro

#### Scenario: Informação não encontrada no contexto
- **WHEN** o contexto recuperado não contém informação suficiente para responder
- **THEN** a resposta indica que não sabe a resposta e `citations` pode ser vazio

### Requirement: Contexto formatado com delimitadores e numeração

O contexto injetado no prompt de geração SHALL apresentar cada documento com um índice numérico sequencial (`[N]`), o nome do livro de origem, e separador visual entre documentos. O formato SHALL permitir ao LLM identificar inequivocamente os limites de cada documento.

#### Scenario: Múltiplos documentos no contexto
- **WHEN** o retrieval retorna 5 documentos de 2 livros diferentes
- **THEN** o contexto enviado ao LLM contém 5 blocos numerados de `[1]` a `[5]`, cada um com `Source:` e conteúdo, separados por delimitadores

#### Scenario: Documento único no contexto
- **WHEN** o retrieval retorna 1 documento
- **THEN** o contexto contém 1 bloco numerado `[1]` com `Source:` e conteúdo
