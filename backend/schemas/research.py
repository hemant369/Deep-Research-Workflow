from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import TypedDict

from schemas.tool_result import ToolResult


PlanSource = Literal["academic", "web", "code"]


class SearchError(TypedDict):
    provider: str
    query: str
    message: str


class ResearchRound(TypedDict):
    round: int
    queries: list[str]
    new_sources: int
    gaps: str


class PlanStepDict(TypedDict):
    id: str
    text: str
    source: PlanSource


class ResearchPlanDict(TypedDict):
    title: str
    steps: list[PlanStepDict]


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=64)
    text: str = Field(..., min_length=1, max_length=500)
    source: PlanSource


class ResearchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., max_length=200)
    steps: list[PlanStep] = Field(..., min_length=1, max_length=10)


class _QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2_000)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        query = value.strip()
        if not query:
            raise ValueError("query must not be blank")
        return query


class PlanRequest(_QueryRequest):
    feedback: str | None = Field(default=None, max_length=1_000)
    previous_plan: ResearchPlan | None = None


class ResearchRequest(_QueryRequest):
    use_memory: bool = False
    # The plan the user approved. Without one, the agent plans by itself.
    plan: ResearchPlan | None = None


class ResearchResponse(BaseModel):
    report: str
    status: str = "completed"
    fatal_error: str = ""
    results: list[ToolResult] = Field(default_factory=list)
    synthesized_text: str = ""
    sub_questions: list[str] = Field(default_factory=list)
    academic_questions: list[str] = Field(default_factory=list)
    general_questions: list[str] = Field(default_factory=list)
    coding_questions: list[str] = Field(default_factory=list)
    search_errors: list[SearchError] = Field(default_factory=list)
    research_round: int = 1
    research_log: list[ResearchRound] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
