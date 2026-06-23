from typing import TypedDict, NotRequired, Annotated
import operator

class ResearchState(TypedDict):
    # Core
    query: str

    # Memory
    memory_hit:   NotRequired[bool]
    past_report:  NotRequired[str]
    past_sources: NotRequired[list]

    # Planner
    sub_questions: NotRequired[list]

    # Router
    academic_questions: list
    general_questions:  list
    coding_questions:   list

    # Agent results
    academic_results: Annotated[list, operator.add]
    general_results:  Annotated[list, operator.add]
    coding_results:   Annotated[list, operator.add]

    # Pipeline
    results:          list
    synthesized_text: str
    report:           str