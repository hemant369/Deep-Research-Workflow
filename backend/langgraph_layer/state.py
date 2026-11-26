from typing_extensions import TypedDict

from schemas.research import ResearchPlanDict, ResearchRound, SearchError
from schemas.tool_result import ToolResult


class ResearchState(TypedDict, total=False):
    query: str
    use_memory: bool
    status: str
    fatal_error: str

    routes: dict[str, list[str]]
    plan: ResearchPlanDict
    sub_questions: list[str]

    academic_questions: list[str]
    general_questions: list[str]
    coding_questions: list[str]

    academic_results: list[ToolResult]
    general_results: list[ToolResult]
    coding_results: list[ToolResult]

    academic_errors: list[SearchError]
    general_errors: list[SearchError]
    coding_errors: list[SearchError]

    search_errors: list[SearchError]
    seen_urls: list[str]
    new_results: list[ToolResult]
    new_evidence_count: int
    results: list[ToolResult]

    research_round: int
    research_log: list[ResearchRound]
    continue_research: bool

    synthesized_text: str
    report: str

    memory_hit: bool
