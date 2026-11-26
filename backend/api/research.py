import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from schemas.research import HealthResponse, PlanRequest, ResearchPlan, ResearchRequest, ResearchResponse
from services.research_runner import draft_plan, run_research, stream_research


logger = logging.getLogger(__name__)
router = APIRouter()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/api/research/plan", response_model=ResearchPlan, tags=["research"])
async def create_plan(request: PlanRequest) -> ResearchPlan:
    """Draft a research plan, or revise `previous_plan` using the user's `feedback`."""
    try:
        return await draft_plan(request)
    except Exception as exc:
        logger.exception("Plan creation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not draft a plan. Check your LLM configuration (Azure OpenAI / Ollama).",
        ) from exc


@router.post(
    "/api/research",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
    tags=["research"],
)
async def research(request: ResearchRequest) -> ResearchResponse:
    try:
        return await run_research(request)
    except Exception as exc:
        logger.exception("Research graph execution failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Research could not be completed.",
        ) from exc


@router.post(
    "/api/research/stream",
    status_code=status.HTTP_200_OK,
    tags=["research"],
)
async def research_stream(request: ResearchRequest) -> StreamingResponse:
    """Stream node-by-node graph execution as Server-Sent Events."""

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event_name, payload in stream_research(request):
            yield _sse(event_name, payload)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
