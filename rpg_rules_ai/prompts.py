from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

PROMPTS_DIR = Path("data/prompts")

DEFAULT_RAG_TEMPLATE = """You are an assistant for question-answering tasks about RPG rules and systems. Use the numbered context passages below to answer the question. If the context does not contain enough information, say you don't know.

Be thorough but focused. Include specific mechanical details directly in the answer: dice rolls, modifiers, penalties, numbers, prerequisites, and step-by-step procedures. The answer text must be self-contained — a reader should understand the full mechanic without reading the citations. Citations are evidence supporting your claims, not a place to put details you left out of the answer.

MANDATORY CITATIONS (academic standard): Treat this like an academic paper. Every single factual statement in your answer MUST be followed by an inline [N] marker citing the context passage that supports it. A sentence without a citation is an unsupported claim and is invalid.

GOOD: "Rapid Strike allows two melee attacks per turn [1], each at -6 to skill [1]. This penalty can be reduced by training [2]."
BAD: "Rapid Strike allows two melee attacks per turn, each at -6 to skill. This penalty can be reduced by training."

An answer without [N] markers will be rejected. The citations list MUST NOT be empty when context passages are provided.

For every [N] marker in your answer, you MUST include a matching citation with:
- "index": the number N matching the [N] marker in the answer text
- "quote": the EXACT verbatim passage copied from the context that supports the claim. Do not paraphrase.
- "source": the book name exactly as shown after "Source:" in the context passage.

Citations should preserve the original language of the context passage.

To make sure that the answer is formatted to the final user, please, use Markdown formatting when writing your answer. Create paragraphs when enumerating lists, to make the reading easier.

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

DEFAULT_CONTEXT_TEMPLATE = """Given this section from {book_name}, under the heading "{section_headers}":

<parent>
{parent_text}
</parent>

Write 2-3 sentences of context for this specific passage. Explain what rule, mechanic, or concept it covers, and note any cross-references to other rules, books, or page numbers mentioned.

<passage>
{child_text}
</passage>"""

DEFAULT_ENTITY_EXTRACTION_TEMPLATE = """Given this passage from {book_name}:

<passage>
{parent_text}
</passage>

Extract all GURPS game entities mentioned (advantages, disadvantages, skills, techniques, maneuvers, spells, equipment, modifiers). For each, indicate:
- name: exact name as written in the text
- type: one of advantage, disadvantage, skill, technique, maneuver, spell, equipment, modifier, other
- mention_type: "defines" if this passage explains or defines the entity (contains its description, cost, mechanics), "references" if it just mentions the entity in passing

Return as a JSON array. If no entities are found, return an empty array."""

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
