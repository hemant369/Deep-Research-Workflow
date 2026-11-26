import asyncio
import logging
import re

from agents.planner_agent import PlannerAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.writer_agent import WriterAgent
from core.config import settings
from core.run_logger import format_json, log_section
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
    logger.info("NODE -> %s searching %s", tool_name, questions)

    try:
        results, raw_errors = await asyncio.wait_for(
            mcp_client.search_batch(tool_name, questions),
            timeout=settings.search_timeout_seconds,
        )
    except Exception as exc:
        message = str(exc) or type(exc).__name__
        logger.warning("NODE -> %s failed: %s", tool_name, message)
        log_section(
            f"SEARCH ERROR ({tool_name})",
            f"Queries: {questions}\nError: {message}",
        )
        return [], [{
            "provider": provider,
            "query": ", ".join(questions),
            "message": message,
        }]

    errors: list[SearchError] = [
        {
            "provider": provider,
            "query": str(error.get("query", "")),
            "message": str(error.get("message", "Unknown search error.")),
        }
        for error in raw_errors
    ]

    logger.info(
        "NODE -> %s returned %d result(s), %d error(s)",
        tool_name,
        len(results),
        len(errors),
    )

    lines = [f"Queries: {questions}", f"Results ({len(results)}):"]
    for idx, item in enumerate(results, start=1):
        meta = item.get("metadata", {})
        extra = ""
        if "full_page" in meta:
            extra = f", full_page={meta['full_page']}"
        elif "has_readme" in meta:
            extra = f", has_readme={meta['has_readme']}"
        lines.append(
            f"  {idx}. [{item.get('source', provider)}] {item.get('title', 'Untitled')}\n"
            f"     URL: {item.get('url', '')}\n"
            f"     Content: {len(item.get('content', ''))} chars{extra}"
        )
    if errors:
        lines.append(f"Errors ({len(errors)}):\n{format_json(errors)}")
    log_section(f"MCP SEARCH ({tool_name})", "\n".join(lines))

    return results, errors


async def memory_load_node(state: ResearchState) -> dict:
    query = state.get("query", "")
    if not query or not state.get("use_memory", False):
        return {"memory_hit": False}

    past = await asyncio.to_thread(memory.find, query)
    if past:
        log_section(
            "MEMORY HIT",
            f"Served cached report from ChromaDB ({len(past['results'])} sources).\n\n{past['report']}",
        )
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
        mode = "from approved plan"
    else:
        routes = await planner.create_search_queries(query)
        mode = "autonomous"
    logger.info("Planner routes (%s): %s", mode, routes)
    log_section(f"PLANNER ({mode})", format_json(routes))
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


def router_node(state: ResearchState) -> dict:
    """Pass the planner's per-source queries to the parallel search branches."""
    routes = state.get("routes", {})
    return {
        "academic_questions": routes.get("academic", []),
        "general_questions": routes.get("general", []),
        "coding_questions": routes.get("coding", []),
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
    logger.info(
        "Merge round %s: %d raw -> %d new unseen result(s)",
        state.get("research_round", 1),
        len(round_results),
        len(new_results),
    )
    log_section(
        f"MERGE (Round {state.get('research_round', 1)})",
        f"Raw this round: {len(round_results)}\n"
        f"New unseen    : {len(new_results)}\n"
        f"Kept so far   : {len(state.get('results', []))}",
    )
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
    cited = citation_generator.execute(state.get("results", []))
    lines = []
    for item in cited:
        lines.append(item.get("reference", item.get("title", "")))
        for passage in item.get("metadata", {}).get("passages", []):
            lines.append(f"  {passage.get('citation', '')} {passage.get('text', '')}")
    if lines:
        log_section("CITATIONS & EXTRACTED PASSAGES", "\n".join(lines))
    return {"results": cited}


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
        log_section("SYNTHESIZER OUTPUT", synthesized_text)
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
        log_section(f"REFLECT (Round {current_round})", f"STOP (round={current_round}, status={state.get('status')})\nGaps:\n{gaps or 'None'}")
        return stop
    if current_round > 1 and not state.get("new_evidence_count"):
        log_section(f"REFLECT (Round {current_round})", "STOP (no new evidence in follow-up round)")
        return stop
    if not gaps:
        log_section(f"REFLECT (Round {current_round})", "STOP (no gaps identified)")
        return stop

    previous_queries = state.get("sub_questions", [])
    routes = await planner.create_followup_queries(state.get("query", ""), gaps, previous_queries)
    new_queries = _flatten(routes)
    if not new_queries:
        log_section(f"REFLECT (Round {current_round})", f"STOP (planner returned no follow-up queries)\nGaps:\n{gaps}")
        return stop

    logger.info("Round %s gaps -> follow-up queries: %s", current_round, new_queries)
    log_section(
        f"REFLECT (Round {current_round}) -> LOOPING TO ROUND {current_round + 1}",
        f"Gaps:\n{gaps}\n\nFollow-up routes:\n{format_json(routes)}",
    )
    return {
        "research_log": log,
        "continue_research": True,
        "routes": routes,
        "sub_questions": previous_queries + new_queries,
        "research_round": current_round + 1,
    }


def reflect_route(state: ResearchState) -> str:
    return "continue" if state.get("continue_research") else "done"


async def writer_node(state: ResearchState) -> dict:
    logger.info("NODE -> writer")
    if state.get("status") in STOPPED:
        return {}
    results = state.get("results", [])
    references = citation_generator.format_references(results)
    try:
        report = await writer.generate_report(
            state.get("query", ""),
            state.get("synthesized_text", ""),
            references,
        )
    except Exception as exc:
        return {"status": "failed", "fatal_error": str(exc)}

    final_report, had_unknown = citation_generator.finalize_report(report, results)
    if had_unknown:
        logger.info("Removed unknown citation markers not present in validated results.")
    log_section("FINAL REPORT", final_report)
    return {
        "report": final_report,
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
