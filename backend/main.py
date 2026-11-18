import json
import logging
from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Literal, cast

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from agents.planner_agent import PlannerAgent
from core.config import settings
from langgraph_layer.graph_builder import build_graph
from langgraph_layer.state import ResearchRound, ResearchState, SearchError
from schemas.tool_result import ToolResult


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

planner = PlannerAgent()


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=64)
    text: str = Field(..., min_length=1, max_length=500)
    source: Literal["academic", "web", "code"]


class ResearchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., max_length=200)
    steps: list[PlanStep] = Field(..., min_length=1, max_length=10)


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2_000)
    feedback: str | None = Field(default=None, max_length=1_000)
    previous_plan: ResearchPlan | None = None

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        query = value.strip()
        if not query:
            raise ValueError("query must not be blank")
        return query


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2_000)
    use_memory: bool = False
    # The plan the user approved. Without one, the agent plans by itself.
    plan: ResearchPlan | None = None

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        query = value.strip()
        if not query:
            raise ValueError("query must not be blank")
        return query


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


def create_app() -> FastAPI:
    application = FastAPI(
        title="Deep Research Agent API",
        version="1.0.0",
        description="Run the deep-research graph and return a completed report.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    return application


app = create_app()


@lru_cache(maxsize=1)
def _research_graph():
    """Compile the graph once and reuse it across requests."""
    return build_graph()


def _payload(request: ResearchRequest) -> ResearchState:
    payload: ResearchState = {
        "query": request.query,
        "use_memory": request.use_memory,
    }
    if request.plan:
        payload["plan"] = request.plan.model_dump()
    return payload


def _search_errors(state: ResearchState) -> list[SearchError]:
    if "search_errors" in state:
        return state["search_errors"]
    return [
        *state.get("academic_errors", []),
        *state.get("general_errors", []),
        *state.get("coding_errors", []),
    ]


def _response_from_state(state: ResearchState) -> ResearchResponse:
    return ResearchResponse(
        report=state.get("report", ""),
        status=state.get("status", "completed"),
        fatal_error=state.get("fatal_error", ""),
        results=state.get("results", []),
        synthesized_text=state.get("synthesized_text", ""),
        sub_questions=state.get("sub_questions", []),
        academic_questions=state.get("academic_questions", []),
        general_questions=state.get("general_questions", []),
        coding_questions=state.get("coding_questions", []),
        search_errors=_search_errors(state),
        research_round=state.get("research_round", 1),
        research_log=state.get("research_log", []),
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/api/research/plan", response_model=ResearchPlan, tags=["research"])
async def create_plan(request: PlanRequest) -> ResearchPlan:
    """Draft a research plan, or revise `previous_plan` using the user's `feedback`."""
    try:
        plan = await planner.create_plan(
            request.query,
            feedback=request.feedback,
            previous_plan=request.previous_plan.model_dump() if request.previous_plan else None,
        )
    except Exception as exc:
        logger.exception("Plan creation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not draft a plan. Is the language model (Ollama) running?",
        ) from exc

    return ResearchPlan(**plan)


@app.post(
    "/api/research",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
    tags=["research"],
)
async def research(request: ResearchRequest) -> ResearchResponse:
    try:
        state = cast(
            ResearchState,
            await _research_graph().ainvoke(_payload(request)),
        )
    except Exception as exc:
        logger.exception("Research graph execution failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Research could not be completed.",
        ) from exc

    return _response_from_state(state)


BRANCH_QUESTION_KEY = {
    "academic": "academic_questions",
    "general": "general_questions",
    "coding": "coding_questions",
}


@app.post(
    "/api/research/stream",
    status_code=status.HTTP_200_OK,
    tags=["research"],
)
async def research_stream(request: ResearchRequest) -> StreamingResponse:
    """Stream node-by-node graph execution as Server-Sent Events."""

    async def event_generator() -> AsyncGenerator[str, None]:
        merged_state: ResearchState = dict(_payload(request))  # type: ignore[assignment]
        try:
            async for chunk in _research_graph().astream(
                _payload(request),
                stream_mode="updates",
            ):
                if not isinstance(chunk, dict):
                    continue
                for node_name, node_update in chunk.items():
                    if isinstance(node_update, dict):
                        merged_state.update(node_update)  # type: ignore[typeddict-item]
                    question_key = BRANCH_QUESTION_KEY.get(node_name)
                    if question_key and not merged_state.get(question_key):
                        continue
                    yield _sse(
                        "stage",
                        {
                            "stage": node_name,
                            "round": merged_state.get("research_round", 1),
                            "continue_research": merged_state.get("continue_research", False),
                            "sub_questions": merged_state.get("sub_questions", []),
                            "sources_count": len(merged_state.get("results", [])),
                            "research_log": merged_state.get("research_log", []),
                        },
                    )
            final_response = _response_from_state(merged_state)
            yield _sse("complete", final_response.model_dump())
        except Exception as exc:
            logger.exception("Streaming research graph execution failed")
            yield _sse(
                "error",
                {"message": str(exc) or "Research could not be completed."},
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
