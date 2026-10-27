"""Request and response shapes of the query API. See docs/phases/phase-5-ui/BRIEF.md."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_QUESTION_CHARS = 4000

Mode = Literal["local", "global", "relate", "baseline"]
Status = Literal["answered", "refused", "clarify"]
CheckStatus = Literal["verified", "warning", "not_checked"]


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(max_length=MAX_QUESTION_CHARS)
    compare: bool = False  # also answer with plain RAG, for the side-by-side view

    @field_validator("question")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be empty")
        return value


class Citation(BaseModel):
    label: str  # "T1", "E2", "C3": the label used inside the answer text
    kind: Literal["text_unit", "entity", "community"]
    title: str
    text: str  # the passage or description; shown as text only, never as HTML
    source: str | None = None  # paper title or section, when known
    ref_id: str | None = None  # id of the text unit, entity or community, for the trace


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # ontology entity type, for example Method or Dataset
    confidence: float | None = None


class GraphLink(BaseModel):
    source: str
    target: str
    predicate: str  # ontology relation name, for example EVALUATED_ON
    confidence: float | None = None


class Answer(BaseModel):
    mode: Mode
    status: Status
    text: str = ""
    message: str | None = None  # why the system refused, or which entity it needs clarified
    citations: list[Citation] = []
    nodes: list[GraphNode] = []
    links: list[GraphLink] = []
    check_status: CheckStatus = "not_checked"
    model: str = ""
    cost_usd: float = 0.0
    latency_ms: int = 0


class AskResponse(BaseModel):
    answer_id: str
    answer: Answer
    baseline: Answer | None = None  # only when compare was requested
    fixture: bool = False  # true when replayed from saved data, not computed now
    saved: bool = False  # false when the answer could not be stored (feedback is then off)


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_id: UUID
    rating: Literal["up", "down"]
    reason: (
        Literal["wrong_answer", "missing_evidence", "wrong_connection", "too_slow", "other"] | None
    ) = None
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    saved: bool
