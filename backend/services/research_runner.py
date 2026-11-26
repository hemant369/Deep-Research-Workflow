import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import cast

from agents.planner_agent import PlannerAgent
from core.observability import aflush_langfuse, langfuse_trace
from core.run_logger import finish_run_log, start_run_log
from langgraph_layer.graph_builder import build_graph
from langgraph_layer.state import ResearchState
from schemas.research import (
    PlanRequest,
    ResearchPlan,
    ResearchPlanDict,
    ResearchRequest,
    ResearchResponse,
    SearchError,
)


logger = logging.getLogger(__name__)

planner = PlannerAgent()

BRANCH_QUESTION_KEY = {
    "academic": "academic_questions",
    "general": "general_questions",
    "coding": "coding_questions",
}


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
        payload["plan"] = cast(ResearchPlanDict, request.plan.model_dump())
    return payload


def _search_errors(state: ResearchState) -> list[SearchError]:
    if "search_errors" in state:
        return state["search_errors"]
    return [
        *state.get("academic_errors", []),
        *state.get("general_errors", []),
        *state.get("coding_errors", []),
    ]


def response_from_state(state: ResearchState) -> ResearchResponse:
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


@asynccontextmanager
async def _tracked_run(request: ResearchRequest, *, mode: str, initial_status: str):
    """Open and close a per-run provenance log file around one graph execution."""
    trace, token = start_run_log(
        request.query,
        mode=mode,
        plan=request.plan.model_dump() if request.plan else None,
        use_memory=request.use_memory,
    )
    outcome = {"status": initial_status, "sources": 0, "error": ""}
    try:
        yield outcome
    finally:
        finish_run_log(
            trace,
            token,
            status=str(outcome["status"]),
            sources_count=int(outcome["sources"]),
            error=str(outcome["error"]),
        )


async def draft_plan(request: PlanRequest) -> ResearchPlan:
    """Create a new research plan or revise a previous plan from user feedback."""
    tags = ["hitl-revision" if request.feedback else "hitl-plan"]
    meta = {"query": request.query, "has_feedback": bool(request.feedback)}
    with langfuse_trace("deep-research-plan", metadata=meta, tags=tags) as lf_config:
        try:
            plan = await planner.create_plan(
                request.query,
                feedback=request.feedback,
                previous_plan=request.previous_plan.model_dump() if request.previous_plan else None,
                config=lf_config or None,
            )
            return ResearchPlan(**plan)
        finally:
            await aflush_langfuse()


async def run_research(request: ResearchRequest) -> ResearchResponse:
    """Execute the research graph to completion and return the final response."""
    async with _tracked_run(request, mode="POST /api/research", initial_status="failed") as outcome:
        meta = {"query": request.query, "use_memory": request.use_memory, "has_plan": bool(request.plan)}
        with langfuse_trace("deep-research-run", metadata=meta, tags=["sync"]) as lf_config:
            try:
                state = cast(
                    ResearchState,
                    await _research_graph().ainvoke(
                        _payload(request),
                        config=cast(dict, lf_config) if lf_config else None,
                    ),
                )
                outcome["status"] = state.get("status", "completed")
                outcome["sources"] = len(state.get("results", []))
                outcome["error"] = state.get("fatal_error", "")
                return response_from_state(state)
            except Exception as exc:
                outcome["error"] = str(exc) or type(exc).__name__
                raise
            finally:
                await aflush_langfuse()


async def stream_research(request: ResearchRequest) -> AsyncGenerator[tuple[str, dict], None]:
    """Stream `(event_name, payload)` updates while running the research graph."""
    async with _tracked_run(request, mode="POST /api/research/stream", initial_status="aborted") as outcome:
        merged_state: ResearchState = dict(_payload(request))  # type: ignore[assignment]
        meta = {"query": request.query, "use_memory": request.use_memory, "has_plan": bool(request.plan)}
        with langfuse_trace("deep-research-stream", metadata=meta, tags=["stream"]) as lf_config:
            try:
                async for chunk in _research_graph().astream(
                    _payload(request),
                    config=cast(dict, lf_config) if lf_config else None,
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
                        yield (
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
                final_response = response_from_state(merged_state)
                outcome["status"] = final_response.status
                outcome["sources"] = len(final_response.results)
                outcome["error"] = final_response.fatal_error
                yield ("complete", final_response.model_dump())
            except Exception as exc:
                outcome["status"] = "failed"
                outcome["sources"] = len(merged_state.get("results", []))
                outcome["error"] = str(exc) or type(exc).__name__
                logger.exception("Streaming research graph execution failed")
                yield ("error", {"message": str(exc) or "Research could not be completed."})
            finally:
                await aflush_langfuse()
