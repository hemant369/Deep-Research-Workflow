from typing import TypedDict

class ResearchState(TypedDict, total=False):
    query: str

    sub_questions: list[str]

    academic_questions: list[str]
    general_questions: list[str]
    coding_questions: list[str]

    academic_results: list
    general_results: list
    coding_results: list

    results: list

    synthesized_text: str
    report: str

    memory_hit: bool
    past_report: str
    past_sources: list