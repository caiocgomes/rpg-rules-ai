import json
import os
import re
from difflib import SequenceMatcher
from html import escape as html_escape

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from rpg_rules_ai.config import settings
from rpg_rules_ai.prompts import get_rag_prompt
from rpg_rules_ai.schemas import AnswerWithSources, State
from rpg_rules_ai.strategies import get_strategy

MAX_HISTORY_PAIRS = 20

_REWRITE_PROMPT = (
    "Given the conversation history and a follow-up question, rewrite the question "
    "to be a standalone question that captures all necessary context. "
    "If the question is already standalone, return it unchanged. "
    "Return ONLY the rewritten question, nothing else."
)

_FUZZY_MATCH_THRESHOLD = 0.5

_CITATION_RETRY_MESSAGE = (
    "Your previous answer contained no inline [N] citation markers. "
    "This is invalid. You MUST include at least one [N] marker in the answer text "
    "referencing the numbered context passages, and a matching entry in the citations list. "
    "Rewrite your answer with proper citations."
)

_NO_CITED_ANSWER_FALLBACK: AnswerWithSources = {
    "answer": "I found relevant passages but could not produce a properly cited answer. "
    "Please try rephrasing your question.",
    "sources": [],
    "citations": [],
    "see_also": [],
}


def _find_best_substring(needle: str, haystack: str) -> str | None:
    """Find the substring in haystack that best matches needle via fuzzy match.

    Uses a sliding window approach: tries windows of varying sizes around the
    needle length, returns the best match above the threshold.
    """
    if not needle or not haystack:
        return None

    needle_lower = needle.lower()
    haystack_lower = haystack.lower()

    # Try exact substring first
    if needle_lower in haystack_lower:
        start = haystack_lower.index(needle_lower)
        return haystack[start : start + len(needle)]

    best_ratio = 0.0
    best_start = 0
    best_end = 0
    n_len = len(needle_lower)

    # Try windows from 0.7x to 1.3x the needle length
    min_window = max(20, int(n_len * 0.7))
    max_window = min(len(haystack_lower), int(n_len * 1.3))

    for win_size in range(min_window, max_window + 1, max(1, (max_window - min_window) // 20)):
        for start in range(0, len(haystack_lower) - win_size + 1, max(1, win_size // 10)):
            candidate = haystack_lower[start : start + win_size]
            ratio = SequenceMatcher(None, needle_lower, candidate, autojunk=False).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = start
                best_end = start + win_size

    if best_ratio >= _FUZZY_MATCH_THRESHOLD:
        return haystack[best_start:best_end]
    return None


def _ground_citations(
    response: AnswerWithSources, context_map: dict[int, str]
) -> AnswerWithSources:
    """Replace LLM-generated quotes with the actual verbatim text from context."""
    citations = response.get("citations", [])
    if not citations or not context_map:
        return response

    grounded = []
    for cit in citations:
        idx = cit.get("index")
        llm_quote = cit.get("quote", "")
        original_text = context_map.get(idx, "")

        if original_text and llm_quote:
            matched = _find_best_substring(llm_quote, original_text)
            if matched:
                cit = {**cit, "quote": matched}

        grounded.append(cit)

    return {**response, "citations": grounded}


def _validate_citations(response: AnswerWithSources) -> AnswerWithSources:
    """Ensure consistency between [N] markers in text and citation indices."""
    answer_text = response.get("answer", "")
    citations = response.get("citations", [])

    markers_in_text = {int(m) for m in re.findall(r"\[(\d+)\]", answer_text)}

    if not markers_in_text:
        return response

    valid_citations = [c for c in citations if c.get("index") in markers_in_text]

    valid_indices = {c["index"] for c in valid_citations}
    orphan_markers = markers_in_text - valid_indices
    cleaned_text = answer_text
    for m in orphan_markers:
        cleaned_text = cleaned_text.replace(f"[{m}]", "")
    cleaned_text = re.sub(r"\s{2,}", " ", cleaned_text).strip()

    valid_citations.sort(key=lambda c: c["index"])

    # Derive sources from actual citations to avoid listing uncited books
    cited_sources = list(dict.fromkeys(
        c["source"] for c in valid_citations if c.get("source")
    ))

    return {
        **response,
        "answer": cleaned_text,
        "citations": valid_citations,
        "sources": cited_sources,
    }


def _has_valid_citations(response: AnswerWithSources) -> bool:
    """Check if response has at least one citation with a matching [N] marker."""
    citations = response.get("citations", [])
    if not citations:
        return False
    answer_text = response.get("answer", "")
    markers = {int(m) for m in re.findall(r"\[(\d+)\]", answer_text)}
    return bool(markers & {c.get("index") for c in citations})


def _enrich_citations_with_context(
    response: AnswerWithSources, context_map: dict[int, str]
) -> AnswerWithSources:
    """Add full parent text with highlighted quote to each citation."""
    citations = response.get("citations", [])
    if not citations or not context_map:
        return response

    enriched = []
    for cit in citations:
        idx = cit.get("index")
        full_text = context_map.get(idx, "")
        quote = cit.get("quote", "")

        if full_text and quote:
            escaped_full = html_escape(full_text)
            escaped_quote = html_escape(quote)
            if escaped_quote in escaped_full:
                highlighted = escaped_full.replace(
                    escaped_quote,
                    f"<mark>{escaped_quote}</mark>",
                    1,
                )
            else:
                highlighted = escaped_full
            cit = {**cit, "context_html": highlighted}
        enriched.append(cit)

    return {**response, "citations": enriched}


def _setup_langsmith():
    if settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project


def _get_llm():
    return ChatOpenAI(model=settings.llm_model, temperature=0)


def _get_recent_history(
    messages: list, max_pairs: int = MAX_HISTORY_PAIRS
) -> list[tuple[str, str]]:
    """Extract the last N Human/AI message pairs from the message list.

    Returns list of (human_text, ai_text) tuples, oldest first.
    Only considers messages before the last one (the current question).
    """
    # Exclude the last message (current question)
    previous = messages[:-1] if messages else []
    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(previous) - 1:
        msg = previous[i]
        next_msg = previous[i + 1]
        if isinstance(msg, HumanMessage) and isinstance(next_msg, AIMessage):
            pairs.append((msg.content, next_msg.content))
            i += 2
        else:
            i += 1
    return pairs[-max_pairs:]


def _format_history_for_prompt(pairs: list[tuple[str, str]]) -> str:
    """Format history pairs into a text block for LLM prompts."""
    lines = []
    for human, ai in pairs:
        lines.append(f"User: {human}")
        # Truncate AI responses to avoid token explosion
        try:
            answer_data = json.loads(ai)
            ai_text = answer_data.get("answer", ai)
        except (json.JSONDecodeError, TypeError):
            ai_text = ai
        if len(ai_text) > 500:
            ai_text = ai_text[:500] + "..."
        lines.append(f"Assistant: {ai_text}")
    return "\n".join(lines)


async def rewrite(state: State):
    """Rewrite the user question using chat history for standalone context."""
    current_question = state["messages"][-1].content
    pairs = _get_recent_history(state["messages"])

    if not pairs:
        return {"main_question": current_question}

    history_text = _format_history_for_prompt(pairs)
    llm = ChatOpenAI(model=settings.context_model, temperature=0)
    result = await llm.ainvoke([
        SystemMessage(content=_REWRITE_PROMPT),
        HumanMessage(content=f"Conversation history:\n{history_text}\n\nFollow-up question: {current_question}"),
    ])
    rewritten = result.content.strip()
    return {"main_question": rewritten or current_question}


async def retrieve_with_strategy(state: State):
    strategy = get_strategy()
    return await strategy.execute(state)


async def generate(state: State):
    llm = _get_llm()
    prompt = get_rag_prompt()

    seen = set()
    blocks = []
    context_map: dict[int, str] = {}
    doc_ids: list[str] = []
    idx = 1
    for question in state["questions"].questions:
        for doc in question.context:
            text = doc.metadata.get("original_text", doc.page_content)
            key = (doc.metadata.get("book", ""), text)
            if key in seen:
                continue
            seen.add(key)
            blocks.append(
                f"[{idx}] Source: {doc.metadata['book']}\n{text}"
            )
            context_map[idx] = text
            doc_id = doc.metadata.get("doc_id", "")
            if doc_id and doc_id not in doc_ids:
                doc_ids.append(doc_id)
            idx += 1
    docs_content = "\n---\n".join(blocks)

    prompt_messages = await prompt.ainvoke(
        {"question": state["main_question"], "context": docs_content}
    )

    # Prepend chat history so the LLM can maintain conversational coherence
    history_pairs = _get_recent_history(state["messages"])
    if history_pairs:
        history_text = _format_history_for_prompt(history_pairs)
        history_msg = SystemMessage(
            content=f"Previous conversation for context (answer coherently with this history):\n{history_text}"
        )
        all_messages = [history_msg] + (
            prompt_messages.to_messages()
            if hasattr(prompt_messages, "to_messages")
            else [prompt_messages]
        )
    else:
        all_messages = prompt_messages

    structured_llm = llm.with_structured_output(AnswerWithSources)
    response = await structured_llm.ainvoke(all_messages)
    response = _ground_citations(response, context_map)
    response = _validate_citations(response)

    # Retry once if context was available but no citations survived
    if context_map and not _has_valid_citations(response):
        base_messages = (
            all_messages if isinstance(all_messages, list)
            else all_messages.to_messages() if hasattr(all_messages, "to_messages")
            else [all_messages]
        )
        retry_messages = base_messages + [
            HumanMessage(content=_CITATION_RETRY_MESSAGE)
        ]
        response = await structured_llm.ainvoke(retry_messages)
        response = _ground_citations(response, context_map)
        response = _validate_citations(response)

    # Fallback if retry also failed
    if context_map and not _has_valid_citations(response):
        response = {**_NO_CITED_ANSWER_FALLBACK}

    response = _enrich_citations_with_context(response, context_map)
    response["doc_ids"] = doc_ids

    return {"answer": response, "messages": [AIMessage(content=json.dumps(response))]}


def build_graph():
    _setup_langsmith()

    graph_builder = StateGraph(State)
    graph_builder.add_node("rewrite", rewrite)
    graph_builder.add_node("retrieve", retrieve_with_strategy)
    graph_builder.add_node("generate", generate)
    graph_builder.add_edge(START, "rewrite")
    graph_builder.add_edge("rewrite", "retrieve")
    graph_builder.add_edge("retrieve", "generate")
    graph_builder.add_edge("generate", END)

    return graph_builder.compile(checkpointer=MemorySaver())
