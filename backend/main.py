import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.langgraph_layer.graph_builder import build_graph


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    use_memory: bool = False


class ResearchResponse(BaseModel):
    report: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    synthesized_text: str = ""
    sub_questions: list[str] = Field(default_factory=list)
    academic_questions: list[str] = Field(default_factory=list)
    general_questions: list[str] = Field(default_factory=list)
    coding_questions: list[str] = Field(default_factory=list)


app = FastAPI(title="Deep Research Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _payload(request: ResearchRequest) -> dict[str, Any]:
    return {
        "query": request.query.strip(),
        "use_memory": request.use_memory,
    }


def _response_from_state(state: dict[str, Any]) -> ResearchResponse:
    return ResearchResponse(
        report=state.get("report", ""),
        results=state.get("results", []),
        synthesized_text=state.get("synthesized_text", ""),
        sub_questions=state.get("sub_questions", []),
        academic_questions=state.get("academic_questions", []),
        general_questions=state.get("general_questions", []),
        coding_questions=state.get("coding_questions", []),
    )


async def _stream_graph_updates(payload: dict[str, Any]) -> AsyncIterator[str]:
    graph = build_graph()
    final_state = dict(payload)

    yield json.dumps({"type": "start", "state": final_state}) + "\n"

    async for update in graph.astream(payload, stream_mode="updates"):
        for node_name, node_update in update.items():
            if isinstance(node_update, dict):
                final_state.update(node_update)

            yield json.dumps({
                "type": "stage",
                "stage": node_name,
                "state": node_update if isinstance(node_update, dict) else {},
            }) + "\n"

    yield json.dumps({
        "type": "complete",
        "response": _response_from_state(final_state).model_dump(),
    }) + "\n"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/research", response_model=ResearchResponse)
async def research(request: ResearchRequest) -> ResearchResponse:
    graph = build_graph()
    state = await graph.ainvoke(_payload(request))
    return _response_from_state(state)


@app.post("/api/research/stream")
async def research_stream(request: ResearchRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_graph_updates(_payload(request)),
        media_type="application/x-ndjson",
    )
