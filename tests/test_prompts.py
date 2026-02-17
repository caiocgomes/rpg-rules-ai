import pytest
from langchain_core.prompts import ChatPromptTemplate

from caprag.prompts import (
    DEFAULT_MULTI_QUESTION_TEMPLATE,
    DEFAULT_RAG_TEMPLATE,
    PROMPT_CONFIGS,
    _load_prompt,
    get_multi_question_prompt,
    get_prompt_content,
    get_rag_prompt,
    reset_prompt,
    save_prompt,
)


@pytest.fixture(autouse=True)
def fake_prompts_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("caprag.prompts.PROMPTS_DIR", tmp_path)
    return tmp_path


def test_load_prompt_returns_default_when_no_file():
    prompt = _load_prompt("rag")
    assert isinstance(prompt, ChatPromptTemplate)
    assert "question" in prompt.input_variables
    assert "context" in prompt.input_variables


def test_load_prompt_reads_from_file(fake_prompts_dir):
    custom = "Custom template: {question} {context}"
    (fake_prompts_dir / "rag.txt").write_text(custom, encoding="utf-8")
    prompt = _load_prompt("rag")
    assert isinstance(prompt, ChatPromptTemplate)
    assert "question" in prompt.input_variables


def test_get_rag_prompt_returns_template():
    prompt = get_rag_prompt()
    assert isinstance(prompt, ChatPromptTemplate)
    assert "question" in prompt.input_variables
    assert "context" in prompt.input_variables


def test_get_multi_question_prompt_returns_template():
    prompt = get_multi_question_prompt()
    assert isinstance(prompt, ChatPromptTemplate)
    assert "messages" in prompt.input_variables


def test_get_prompt_content_returns_default_when_no_file():
    content = get_prompt_content("rag")
    assert content == DEFAULT_RAG_TEMPLATE


def test_get_prompt_content_returns_file_content(fake_prompts_dir):
    custom = "my custom rag prompt"
    (fake_prompts_dir / "rag.txt").write_text(custom, encoding="utf-8")
    assert get_prompt_content("rag") == custom


def test_save_prompt_creates_dir_and_writes(fake_prompts_dir):
    subdir = fake_prompts_dir / "nested"
    import caprag.prompts as mod
    mod.PROMPTS_DIR = subdir

    save_prompt("rag", "saved content")
    assert (subdir / "rag.txt").read_text(encoding="utf-8") == "saved content"

    mod.PROMPTS_DIR = fake_prompts_dir


def test_save_prompt_writes_file(fake_prompts_dir):
    save_prompt("multi_question", "new multi q")
    assert (fake_prompts_dir / "multi_question.txt").read_text(encoding="utf-8") == "new multi q"


def test_reset_prompt_deletes_existing_file(fake_prompts_dir):
    path = fake_prompts_dir / "rag.txt"
    path.write_text("something", encoding="utf-8")
    assert path.exists()
    reset_prompt("rag")
    assert not path.exists()


def test_reset_prompt_noop_when_no_file():
    reset_prompt("rag")
