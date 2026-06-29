from typing_extensions import TypedDict
from backend.schemas.tool_result import ToolResult

class ResearchState(TypedDict, total=False):
    query: str
    use_memory: bool

    sub_questions: list[str]

    academic_questions: list[str]
    general_questions: list[str]
    coding_questions: list[str]

    academic_results: list[ToolResult]
    general_results: list[ToolResult]
    coding_results: list[ToolResult]

    results: list[ToolResult]

    synthesized_text: str
    report: str

    memory_hit: bool
    past_report: str
    past_sources: list
