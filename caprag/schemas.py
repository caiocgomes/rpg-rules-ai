from typing import List, Literal, Optional

from langchain_core.documents import Document
from langgraph.graph.message import MessagesState
from pydantic import BaseModel, Field
from typing_extensions import Annotated, TypedDict


class ProgressUpdate(TypedDict):
    filename: str
    status: Literal["success", "skipped", "error"]
    completed: int
    total: int
    error_message: Optional[str]


class Citation(TypedDict):
    index: Annotated[
        int,
        ...,
        "The citation number matching the [N] marker in the answer text.",
    ]
    quote: Annotated[
        str,
        ...,
        "The VERBATIM quote from the specified source that justifies the answer. "
        "Always in the same language as the original quote.",
    ]
    source: Annotated[
        str,
        ...,
        "Source book where the quote was taken. Cited VERBATIM from the source field.",
    ]


class AnswerWithSources(TypedDict):
    """An answer to the question, with sources and quotations."""

    answer: str
    sources: Annotated[List[str], ..., "List of source books used to answer the question"]
    citations: Annotated[
        List[Citation],
        ...,
        "Citations from sources that justify the answer. Must be in the same language as the context.",
    ]
    see_also: Annotated[
        List[str],
        ...,
        "Terms the user may want to look up to expand the search. "
        "Include terms that reference pages (p. or pp.).",
    ]


class LLMQuestion(BaseModel):
    """Schema sent to the LLM for structured output (no Document fields)."""

    question: str


class LLMQuestions(BaseModel):
    """Schema sent to the LLM for structured output."""

    questions: List[LLMQuestion] = Field(description="List of questions")


class Question(BaseModel):
    question: str
    context: Optional[List[Document]] = Field(
        default=[], description="List of contexts for the specific question"
    )


class Questions(BaseModel):
    questions: List[Question] = Field(description="List of questions")


class State(MessagesState):
    main_question: str
    questions: Annotated[Questions, None, "New questions expanding the original question"]
    answer: Annotated[
        AnswerWithSources,
        None,
        "Final Answer, with Quoted Citation and book of origin",
    ]
