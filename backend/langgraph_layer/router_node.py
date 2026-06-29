import json

from backend.model.llm import llm


ACADEMIC_KEYWORDS = {
    "arxiv", "paper", "papers", "research", "study", "survey", "benchmark",
    "methodology", "evaluation", "experiment", "dataset", "model", "scientific",
    "journal", "conference", "state of the art", "sota",
}

CODING_KEYWORDS = {
    "github", "repo", "repository", "code", "python", "library", "framework",
    "api", "implementation", "sdk", "package", "tool", "example", "tutorial",
}

GENERAL_KEYWORDS = {
    "definition", "overview", "comparison", "advantages", "disadvantages",
    "use cases", "explain", "concept", "trend", "future", "business",
}


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        value = str(value).strip()
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _heuristic_categories(question: str) -> set[str]:
    text = question.lower()
    categories = {"general"}

    if any(keyword in text for keyword in ACADEMIC_KEYWORDS):
        categories.add("academic")
    if any(keyword in text for keyword in CODING_KEYWORDS):
        categories.add("coding")
    if any(keyword in text for keyword in GENERAL_KEYWORDS):
        categories.add("general")

    # Research queries benefit from at least one academic pass unless they are clearly code-only.
    if "coding" not in categories:
        categories.add("academic")

    return categories


def _parse_llm_routes(content: str) -> dict[str, set[str]]:
    content = content.replace("```json", "").replace("```", "").strip()
    routes = json.loads(content)
    parsed: dict[str, set[str]] = {}

    if not isinstance(routes, list):
        raise ValueError("Router output must be a JSON array.")

    for item in routes:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        categories = {
            str(category).strip().lower()
            for category in item.get("categories", [])
            if str(category).strip().lower() in {"academic", "coding", "general"}
        }
        if question and categories:
            parsed[question] = categories

    return parsed


async def router_node(state):
    print("NODE -> Router Node")
    sub_questions = state["sub_questions"]

    if not sub_questions:
        return {
            "academic_questions": [],
            "coding_questions": [],
            "general_questions": []
        }

    prompt = f"""You are an intelligent research router.
        Classify each search query into one or more categories.

        Categories:
        Academic - papers, studies, surveys, benchmarks, methods, datasets
        Coding - GitHub repositories, source code, libraries, APIs, implementations
        General - explanations, comparisons, use cases, trends, practical context

        Questions:
        {sub_questions}

        Rules:
        1. A question may belong to multiple categories.
        2. Prefer recall over precision. If unsure, include General.
        3. Return ONLY a valid JSON array, no markdown, no explanation.
        4. Output format:
        [
            {{"question": "...", "categories": ["Academic", "General"], "priority": "High"}}
        ]
        """

    llm_routes: dict[str, set[str]] = {}
    content = ""
    try:
        response = llm.invoke(prompt)
        content = response.content
        if not isinstance(content, str):
            raise ValueError("Router did not return a string.")
        llm_routes = _parse_llm_routes(content)
    except Exception as e:
        print(f"\nROUTER ERROR: {e}")
        print(f"\nROUTER OUTPUT: {content}")

    academic_questions, coding_questions, general_questions = [], [], []

    for question in sub_questions:
        categories = _heuristic_categories(question)
        categories.update(llm_routes.get(question, set()))

        if "academic" in categories:
            academic_questions.append(question)
        if "coding" in categories:
            coding_questions.append(question)
        if "general" in categories:
            general_questions.append(question)

    return {
        "academic_questions": _dedupe(academic_questions),
        "coding_questions": _dedupe(coding_questions),
        "general_questions": _dedupe(general_questions)
    }
