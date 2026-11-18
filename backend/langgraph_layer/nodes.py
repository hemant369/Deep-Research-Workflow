import asyncio
import logging
import re

from agents.planner_agent import PlannerAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.writer_agent import WriterAgent
from core.config import settings
from langgraph_layer.state import ResearchState, SearchError
from mcp_layer.client import MCPClient
from memory.memory_store import memory
from schemas.tool_result import ToolResult
from services.citation_generator import CitationGenerator
from services.evidence_validator import EvidenceValidator
from services.merge_dedup import remove_duplicates, result_key


logger = logging.getLogger(__name__)

planner = PlannerAgent()
mcp_client = MCPClient()
validator = EvidenceValidator()
citation_generator = CitationGenerator()
synthesizer = SynthesizerAgent()
writer = WriterAgent()

STOPPED = {"failed", "insufficient_evidence"}
CITATION_PATTERN = re.compile(r"\[(\d+)(?:\.(\d+))?\](?!\()")


def _flatten(routes: dict[str, list[str]]) -> list[str]:
    return list(dict.fromkeys(q for queries in routes.values() for q in queries))


async def _search(
    tool_name: str,
    questions: list[str],
) -> tuple[list[ToolResult], list[SearchError]]:
    """Call one MCP batch tool and convert failures to graph state."""
    if not questions:
        return [], []

    provider = tool_name.removesuffix("_search")

    try:
        results, raw_errors = await asyncio.wait_for(
            mcp_client.search_batch(tool_name, questions),
            timeout=settings.search_timeout_seconds,
        )
    except Exception as exc:
        return [], [{
            "provider": provider,
            "query": ", ".join(questions),
            "message": str(exc) or type(exc).__name__,
        }]

    errors: list[SearchError] = [
        {
            "provider": provider,
            "query": str(error.get("query", "")),
            "message": str(error.get("message", "Unknown search error.")),
        }
        for error in raw_errors
    ]

    return results, errors


async def memory_load_node(state: ResearchState) -> dict:
    query = state.get("query", "")
    if not query or not state.get("use_memory", False):
        return {"memory_hit": False}

    past = await asyncio.to_thread(memory.find, query)
    if past:
        return {
            "memory_hit": True,
            "report": past["report"],
            "results": past["results"],
            "status": "completed",
        }
    return {"memory_hit": False}


async def planner_node(state: ResearchState) -> dict:
    """Turn the user-approved plan into search queries (or plan from scratch if none was given)."""
    logger.info("NODE -> planner")
    query = state.get("query", "")
    plan = state.get("plan")
    if plan and plan.get("steps"):
        routes = await planner.queries_from_plan(query, plan)
    else:
        routes = await planner.create_search_queries(query)
    return {
        "routes": routes,
        "sub_questions": _flatten(routes),
        "research_round": 1,
        "research_log": [],
        "search_errors": [],
        "seen_urls": [],
        "results": [],
        "status": "running",
    }


async def general_node(state: ResearchState) -> dict:
    results, errors = await _search(
        "web_search", state.get("general_questions", [])
    )
    return {"general_results": results, "general_errors": errors}


async def academic_node(state: ResearchState) -> dict:
    results, errors = await _search(
        "arxiv_search", state.get("academic_questions", [])
    )
    return {"academic_results": results, "academic_errors": errors}


async def coding_node(state: ResearchState) -> dict:
    results, errors = await _search(
        "github_search", state.get("coding_questions", [])
    )
    return {"coding_results": results, "coding_errors": errors}


async def merge_node(state: ResearchState) -> dict:
    """Combine this round's search output, keeping only sources not seen in earlier rounds."""
    logger.info("NODE -> merge (round %s)", state.get("research_round", 1))
    round_results = (
        state.get("academic_results", []) +
        state.get("general_results", []) +
        state.get("coding_results", [])
    )
    seen = set(state.get("seen_urls", []))
    new_results = [
        result for result in remove_duplicates(round_results)
        if result_key(result) not in seen
    ]
    search_errors = (
        state.get("search_errors", []) +
        state.get("academic_errors", []) +
        state.get("general_errors", []) +
        state.get("coding_errors", [])
    )
    update: dict = {
        "new_results": new_results,
        "seen_urls": [*seen, *(result_key(result) for result in new_results)],
        "search_errors": search_errors,
    }
    if not new_results and not state.get("results"):
        update.update({
            "status": "insufficient_evidence",
            "fatal_error": "No search results were found.",
        })
    return update


async def validator_node(state: ResearchState) -> dict:
    """Validate only the new sources, then add them to the evidence kept from earlier rounds."""
    logger.info("NODE -> validator")
    if state.get("status") in STOPPED:
        return {}

    existing = state.get("results", [])
    new_results = state.get("new_results", [])
    try:
        validated = await validator.execute(state.get("query", ""), new_results) if new_results else []
    except Exception as exc:
        if existing:
            logger.warning("Validation failed in a follow-up round: %s", exc)
            return {"new_evidence_count": 0}
        return {"results": [], "status": "failed", "fatal_error": str(exc)}

    results = sorted(
        existing + validated,
        key=lambda item: item.get("confidence", 0),
        reverse=True,
    )[:settings.max_total_sources]

    if not results:
        return {
            "results": [],
            "new_evidence_count": 0,
            "status": "insufficient_evidence",
            "fatal_error": "No relevant evidence was found for this question.",
        }
    return {"results": results, "new_evidence_count": len(validated)}


async def citation_node(state: ResearchState) -> dict:
    logger.info("NODE -> citation")
    if state.get("status") in STOPPED:
        return {}
    return {"results": citation_generator.execute(state.get("results", []))}


async def synthesizer_node(state: ResearchState) -> dict:
    logger.info("NODE -> synthesizer")
    if state.get("status") in STOPPED:
        return {}
    previous = state.get("synthesized_text", "")
    if previous and not state.get("new_evidence_count"):
        return {}
    try:
        synthesized_text = await synthesizer.synthesize(
            state.get("query", ""),
            state.get("results", []),
        )
        return {"synthesized_text": synthesized_text}
    except Exception as exc:
        if previous:
            logger.warning("Re-synthesis failed; keeping the previous synthesis: %s", exc)
            return {}
        return {"status": "failed", "fatal_error": str(exc)}


def _extract_gaps(synthesized_text: str) -> str:
    """Return the GAPS section of the synthesis, or '' if it reports no real gaps."""
    match = re.search(r"GAPS:?\s*(.*)", synthesized_text, flags=re.IGNORECASE | re.DOTALL)
    gaps = match.group(1).strip() if match else ""
    if re.fullmatch(
        r"[-*\s]*(none( identified)?|n/?a|no (significant |major )?gaps( identified)?)?[^\w]*",
        gaps,
        flags=re.IGNORECASE,
    ):
        return ""
    return gaps


async def reflect_node(state: ResearchState) -> dict:
    """Reflection step of the deep-research loop.

    Reads the GAPS found by the synthesizer and decides whether another search round
    is worthwhile. If so, it plans follow-up queries that target those gaps.
    """
    logger.info("NODE -> reflect")
    current_round = state.get("research_round", 1)
    gaps = _extract_gaps(state.get("synthesized_text", ""))
    log = state.get("research_log", []) + [{
        "round": current_round,
        "queries": _flatten(state.get("routes", {})),
        "new_sources": state.get("new_evidence_count", 0),
        "gaps": gaps,
    }]
    stop = {"research_log": log, "continue_research": False}

    if state.get("status") in STOPPED or current_round >= settings.max_research_rounds:
        return stop
    if current_round > 1 and not state.get("new_evidence_count"):
        return stop
    if not gaps:
        return stop

    previous_queries = state.get("sub_questions", [])
    routes = await planner.create_followup_queries(state.get("query", ""), gaps, previous_queries)
    new_queries = _flatten(routes)
    if not new_queries:
        return stop

    logger.info("Round %s gaps -> follow-up queries: %s", current_round, new_queries)
    return {
        "research_log": log,
        "continue_research": True,
        "routes": routes,
        "sub_questions": previous_queries + new_queries,
        "research_round": current_round + 1,
    }


def reflect_route(state: ResearchState) -> str:
    return "continue" if state.get("continue_research") else "done"


def _format_references(results: list[ToolResult], cited: set[int] | None = None) -> str:
    return "\n".join(
        f"- {item.get('reference', '')}"
        for index, item in enumerate(results, start=1)
        if item.get("reference") and (not cited or index in cited)
    )


def _cited_source_indices(report: str) -> set[int]:
    return {int(match.group(1)) for match in CITATION_PATTERN.finditer(report)}


def _remove_unknown_citations(report: str, results: list[ToolResult]) -> str:
    """Drop citation markers like [7] or [7.2] that point to no real source/passage."""
    valid: set[str] = set()
    for source_index, item in enumerate(results, start=1):
        valid.add(str(source_index))
        for passage in item.get("metadata", {}).get("passages", []):
            if passage.get("passage_id"):
                valid.add(passage["passage_id"])

    def replace(match: re.Match) -> str:
        key = match.group(1) if match.group(2) is None else f"{match.group(1)}.{match.group(2)}"
        return match.group(0) if key in valid else ""

    return CITATION_PATTERN.sub(replace, report)


def _add_references_to_report(report: str, references: str) -> str:
    report = re.split(r"(?im)^# References\s*$", report, maxsplit=1)[0].rstrip()
    return f"{report}\n\n# References\n{references}".strip()


async def writer_node(state: ResearchState) -> dict:
    logger.info("NODE -> writer")
    if state.get("status") in STOPPED:
        return {}
    results = state.get("results", [])
    references = _format_references(results)
    try:
        report = await writer.generate_report(
            state.get("query", ""),
            state.get("synthesized_text", ""),
            references,
        )
    except Exception as exc:
        return {"status": "failed", "fatal_error": str(exc)}

    report = _remove_unknown_citations(report, results)
    cited_references = _format_references(results, _cited_source_indices(report))
    return {
        "report": _add_references_to_report(report, cited_references),
        "status": "completed",
    }


async def memory_save_node(state: ResearchState) -> dict:
    logger.info("NODE -> memory_save")
    query = state.get("query", "")
    report = state.get("report", "")
    if state.get("status") != "completed" or not query or not report:
        return {}

    await asyncio.to_thread(memory.save, query, report, state.get("results", []))
    return {}
