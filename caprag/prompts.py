from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

PROMPTS_DIR = Path("data/prompts")

DEFAULT_RAG_TEMPLATE = """You are an assistant for question-answering tasks about RPG rules and systems. Use the numbered context passages below to answer the question. If the context does not contain enough information, say you don't know.

Keep your answer concise (three sentences maximum in the "answer" field).

For every factual claim in your answer you MUST include a citation. Each citation MUST contain:
- "quote": the EXACT verbatim passage copied from the context that supports the claim. Do not paraphrase.
- "source": the book name exactly as shown after "Source:" in the context passage.

The citations should preserve the original language of the context passage.

Question: {question}

Context:
{context}

Answer:"""

DEFAULT_MULTI_QUESTION_TEMPLATE = """You are an expert on RPG rules and systems (GURPS, D&D, Savage Worlds, etc.).

Given a user question about RPG rules, break it down into 2-4 focused sub-questions that will help retrieve the most relevant rule passages. Each sub-question should target a specific aspect of the rules (mechanics, modifiers, prerequisites, interactions with other rules, etc.).

Focus on:
- The core mechanic being asked about
- Any modifiers, prerequisites, or costs that apply
- Cross-references to other rules or books that might be relevant
- Edge cases or interactions the user might not have considered

User question: {messages}"""

PROMPT_CONFIGS = {
    "rag": {
        "file": "rag.txt",
        "default": DEFAULT_RAG_TEMPLATE,
        "variables": ["question", "context"],
    },
    "multi_question": {
        "file": "multi_question.txt",
        "default": DEFAULT_MULTI_QUESTION_TEMPLATE,
        "variables": ["messages"],
    },
}


def _load_prompt(name: str) -> ChatPromptTemplate:
    config = PROMPT_CONFIGS[name]
    local_path = PROMPTS_DIR / config["file"]
    if local_path.exists():
        template = local_path.read_text(encoding="utf-8")
    else:
        template = config["default"]
    return ChatPromptTemplate.from_template(template)


def get_rag_prompt() -> ChatPromptTemplate:
    return _load_prompt("rag")


def get_multi_question_prompt() -> ChatPromptTemplate:
    return _load_prompt("multi_question")


def get_prompt_content(name: str) -> str:
    config = PROMPT_CONFIGS[name]
    local_path = PROMPTS_DIR / config["file"]
    if local_path.exists():
        return local_path.read_text(encoding="utf-8")
    return config["default"]


def save_prompt(name: str, content: str) -> None:
    config = PROMPT_CONFIGS[name]
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    (PROMPTS_DIR / config["file"]).write_text(content, encoding="utf-8")


def reset_prompt(name: str) -> None:
    config = PROMPT_CONFIGS[name]
    local_path = PROMPTS_DIR / config["file"]
    if local_path.exists():
        local_path.unlink()
