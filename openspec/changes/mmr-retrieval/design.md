## Context

Mudança independente das outras 3. Pode ser aplicada a qualquer momento porque opera sobre o retriever existente sem mudar o index. Funciona com qualquer chunk strategy.

## Goals / Non-Goals

**Goals:**
- Diversidade de fontes nos resultados de retrieval
- Configurável: lambda_mult controla o balance relevância/diversidade
- Sem overhead perceptível (MMR é O(k*fetch_k), com k=12 e fetch_k=30 são 360 comparações)

**Non-Goals:**
- Diversidade explícita por livro (MMR opera no embedding space, não no metadata)
- Reranking por modelo (cross-encoder, etc.)
- Mudanças no pipeline de ingestão

## Decisions

### 1. Parâmetros MMR

```python
search_type = "mmr"
search_kwargs = {
    "k": 12,           # final selection
    "fetch_k": 30,     # candidate pool
    "lambda_mult": 0.7  # 0=max diversity, 1=pure similarity
}
```

`lambda_mult=0.7` é conservador: 70% relevância, 30% diversidade. O suficiente para quebrar clusters de livro único sem sacrificar relevância. Pode ser tuned depois.

`fetch_k=30` garante pool diverso o suficiente. Com 7 livros no corpus, 30 candidatos provavelmente incluem chunks de 3-5 livros diferentes.

### 2. MMR opera nos child chunks

O ParentDocumentRetriever faz MMR no nível dos children, depois expande para parents. Children do mesmo parent são similares entre si, então MMR tende a selecionar children de parents diferentes, o que é o comportamento desejado.

Limitação: dois children de parents diferentes mas do mesmo livro podem ser muito similares (mesma regra descrita em seções diferentes). MMR não sabe que são do mesmo livro. Para diversidade explícita por livro, seria necessário um retriever custom. Aceitável para v1.

## Risks / Trade-offs

**[Lambda_mult muito baixo pode sacrificar relevância]** → 0.7 é conservador. Se os resultados perderem qualidade, subir para 0.8. Configurável via env var.

**[MMR não garante diversidade de livro]** → Garante diversidade de embedding, que correlaciona com diversidade de livro mas não é a mesma coisa. O entity index (mudança 3) resolve o gap.
