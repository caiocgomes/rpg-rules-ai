## 1. Schema

- [x] 1.1 Add `index: int` field to `Citation` in `caprag/schemas.py`

## 2. Prompt

- [x] 2.1 Rewrite `DEFAULT_RAG_TEMPLATE` in `caprag/prompts.py` with inline citation instructions

## 3. Backend Validation

- [x] 3.1 Add `_validate_citations(answer: AnswerWithSources) -> AnswerWithSources` to `caprag/graph.py`: extract `[N]` from text, filter orphan citations, clean orphan markers
- [x] 3.2 Call `_validate_citations()` on LLM response in `generate()` before returning
- [x] 3.3 Write tests for validation: happy path, orphan citations, orphan markers, no markers (graceful degradation)

## 4. Frontend

- [x] 4.1 Update `chat_answer.html`: process answer text to convert `[N]` to anchor links, render citation blocks below text
- [x] 4.2 Add CSS for `.cite-marker`, `.citations-block`, `.citation-ref`, `.citation-ref:target` to `style.css`

## 5. Cleanup

- [x] 5.1 Update existing tests in `test_graph.py` that depend on `AnswerWithSources` format
- [x] 5.2 Archive `fix-citations` change as superseded
