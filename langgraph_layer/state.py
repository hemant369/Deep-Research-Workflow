from typing import TypedDict, NotRequired

class ResearchState(TypedDict):

    query: str
    sub_questions: NotRequired[list]
    results: NotRequired[list]
    synthesized_text: NotRequired[str]
    report: NotRequired[str]
    