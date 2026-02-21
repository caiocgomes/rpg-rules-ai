## 1. Graph and rewrite node

- [x] 1.1 Add `rewrite` async node in `graph.py` that reads chat history (last 20 pairs) and rewrites the user question to be standalone via LLM call
- [x] 1.2 Add helper `_get_recent_history(messages, max_pairs=20)` that extracts the last N Human/AI message pairs from the state
- [x] 1.3 Update `build_graph()` to add `rewrite` node, wire `START → rewrite → retrieve → generate → END`, and compile with `MemorySaver` checkpointer
- [x] 1.4 Update `generate` node to include recent chat history in the RAG prompt context

## 2. Service and API layer

- [x] 2.1 Change `services.ask_question` signature to accept `thread_id: str | None` and pass it as `config={"configurable": {"thread_id": ...}}` to graph.ainvoke
- [x] 2.2 Update `AskRequest` schema in `api.py` to include optional `thread_id` field; generate UUID server-side if omitted
- [x] 2.3 Update `POST /chat/ask` in `frontend.py` to read `thread_id` from form data and pass to `services.ask_question`

## 3. Frontend

- [x] 3.1 Update `chat.html` to generate a UUID via `crypto.randomUUID()` on page load and include it as a hidden input `thread_id` in the chat form

## 4. Tests

- [x] 4.1 Add tests for `_get_recent_history` helper (empty history, under limit, over 20 pairs)
- [x] 4.2 Add tests for `rewrite` node (standalone passthrough, anaphora resolution, no history)
- [x] 4.3 Add test for graph topology (rewrite → retrieve → generate, checkpointer present)
- [x] 4.4 Add test for `ask_question` with thread_id (two sequential calls share history)
- [x] 4.5 Verify all existing tests still pass
