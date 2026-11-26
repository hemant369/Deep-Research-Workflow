import json
import logging

from model.llm import llm


logger = logging.getLogger(__name__)

CATEGORIES = ("academic", "general", "coding")

# The UI talks about plan steps by source type; the graph talks about search branches.
SOURCE_TO_ROUTE = {"academic": "academic", "web": "general", "code": "coding"}
SOURCE_ALIASES = {
    "academic": "academic", "paper": "academic", "papers": "academic", "arxiv": "academic",
    "web": "web", "general": "web", "article": "web", "articles": "web", "news": "web",
    "code": "code", "coding": "code", "github": "code", "repo": "code", "repository": "code",
}

MAX_PLAN_STEPS = 8
MAX_QUERIES_PER_ROUTE = 3

FORMAT = """- academic: 1-2 queries for arXiv papers.
- general: 1-2 queries for a web search engine.
- coding: 1 query of 2-4 keywords for GitHub repository search,
  or an empty list if code is irrelevant.
Keep each query under 10 words.

Return only JSON:
{"academic": ["..."], "general": ["..."], "coding": ["..."]}"""


def _load_json(content: str) -> dict:
    """Parse the first JSON object in model output (tolerates prose and code fences)."""
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("No JSON object in model output.")
    data = json.loads(content[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("Model output is not a JSON object.")
    return data


def _parse_routes(content: str, exclude: set[str] | None = None) -> dict[str, list[str]]:
    """Parse {"academic": [...], ...} from model output, dropping repeats and excluded queries."""
    data = _load_json(content)
    skip = {q.lower() for q in (exclude or set())}

    routes: dict[str, list[str]] = {}
    for category in CATEGORIES:
        queries = [str(item).strip() for item in data.get(category, []) or []]
        unique = dict.fromkeys(q for q in queries if q and q.lower() not in skip)
        routes[category] = list(unique)[:2]
    return routes


def _normalize_plan(data: dict, query: str) -> dict:
    """Validate a model-written plan; raise ValueError if it has no usable steps."""
    steps = []
    for item in data.get("steps", []) or []:
        if not isinstance(item, dict):
            continue
        text = " ".join(str(item.get("text", "")).split())
        source = SOURCE_ALIASES.get(str(item.get("source", "web")).strip().lower(), "web")
        if text:
            steps.append({"id": f"s{len(steps) + 1}", "text": text[:500], "source": source})
        if len(steps) == MAX_PLAN_STEPS:
            break

    if not steps:
        raise ValueError("Plan has no steps.")

    title = " ".join(str(data.get("title", "")).split()) or query
    return {"title": title[:120], "steps": steps}


def fallback_plan(query: str) -> dict:
    """A generic plan, used only when the model's plan cannot be parsed."""
    return {
        "title": query[:120],
        "steps": [
            {"id": "s1", "text": f"Find research papers and surveys about: {query}", "source": "academic"},
            {"id": "s2", "text": f"Find recent articles and expert analysis about: {query}", "source": "web"},
            {"id": "s3", "text": "Check how this is implemented in practice (open-source projects)", "source": "code"},
        ],
    }


class PlannerAgent:
    async def create_plan(
        self,
        query: str,
        feedback: str | None = None,
        previous_plan: dict | None = None,
        config: dict | None = None,
    ) -> dict:
        """Draft (or revise) a research plan for the user to review.

        A failing model call raises, so the user sees the error instead of a made-up plan.
        If the model answers but the answer cannot be parsed, a generic plan is returned.
        """
        revision = ""
        if feedback and previous_plan:
            revision = f"""
Current plan:
{json.dumps(previous_plan)}

The user wants these changes: {feedback}
Revise the plan to apply them. Keep the steps that still make sense.
"""

        prompt = f"""You are preparing a research plan for the question below. The user will review it before any searching starts.

Question:
{query}
{revision}
Write 4-6 concrete steps. Each step says what to find and which source type to use:
- "academic": research papers on arXiv
- "web": articles, reports, documentation, news
- "code": GitHub repositories (only if code or implementations are relevant)
Include at least one "web" step. End with a step that cross-checks claims or looks for disagreements.

Return only JSON:
{{"title": "short title (under 80 characters)", "steps": [{{"text": "...", "source": "academic|web|code"}}]}}
"""
        response = await llm.ainvoke(prompt, config=config)
        try:
            return _normalize_plan(_load_json(str(response.content)), query)
        except Exception:
            logger.warning("Plan output could not be parsed; using a generic plan.")
            return fallback_plan(query)

    async def queries_from_plan(self, query: str, plan: dict) -> dict[str, list[str]]:
        """Turn the user-approved plan into search queries, grouped by search branch.

        Each step becomes one query on its own source type, so the user's edits decide
        what gets searched (a plan with no "code" step never searches GitHub).
        """
        steps = plan.get("steps", [])
        numbered = [
            {"step": index, "source": step["source"], "text": step["text"]}
            for index, step in enumerate(steps, start=1)
        ]

        prompt = f"""Turn each approved research step into ONE search query.

Overall question: {query}

Steps:
{json.dumps(numbered)}

Rules:
- "academic" queries: 2-5 plain keywords (they are all required to match on arXiv). No filler words.
- "code" queries: 2-4 keywords for GitHub repository search.
- "web" queries: a natural search-engine query under 10 words.
- Keep the subject (company, product, technique) named in the question in every query.

Return only JSON with one query per step, in order:
{{"queries": ["query for step 1", "query for step 2"]}}
"""
        queries: list = []
        try:
            response = await llm.ainvoke(prompt)
            raw = _load_json(str(response.content)).get("queries", [])
            queries = raw if isinstance(raw, list) else []
        except Exception:
            logger.warning("Could not turn the plan into queries; using the step text.")

        routes: dict[str, list[str]] = {category: [] for category in CATEGORIES}
        for index, step in enumerate(steps):
            written = str(queries[index]).strip() if index < len(queries) else ""
            search = written or " ".join(step["text"].split()[:10])
            routes[SOURCE_TO_ROUTE[step["source"]]].append(search)

        return {
            category: list(dict.fromkeys(items))[:MAX_QUERIES_PER_ROUTE]
            for category, items in routes.items()
        }

    async def create_search_queries(self, query: str) -> dict[str, list[str]]:
        """Return short search queries grouped by the source that should run them."""
        prompt = f"""Create short search queries for this research topic:

{query}

{FORMAT}
"""
        try:
            response = await llm.ainvoke(prompt)
            routes = _parse_routes(str(response.content))
            if any(routes.values()):
                return routes
        except Exception:
            logger.warning("Planner output could not be parsed; using the raw query.")

        return {"academic": [query], "general": [query], "coding": []}

    async def create_followup_queries(
        self,
        query: str,
        gaps: str,
        previous_queries: list[str],
    ) -> dict[str, list[str]]:
        """Plan new searches that target knowledge gaps found in the last round."""
        prompt = f"""You are planning the next round of a research investigation.

Research question:
{query}

Knowledge gaps found so far:
{gaps}

Queries already searched (do NOT repeat them):
{json.dumps(previous_queries)}

Write NEW search queries that would fill the most important gaps.
If the gaps are minor or cannot be answered by searching, return empty lists.

{FORMAT}
"""
        try:
            response = await llm.ainvoke(prompt)
            return _parse_routes(str(response.content), exclude=set(previous_queries))
        except Exception:
            logger.warning("Follow-up planning failed; stopping the research loop.")
            return {category: [] for category in CATEGORIES}
