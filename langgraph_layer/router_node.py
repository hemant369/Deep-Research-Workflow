import json
from model.llm import llm

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
        Your task is to classify each question into one or more categories.

        Categories:

        Academic
        - Research papers, scientific studies, surveys, benchmarks, methodologies, journals

        Coding
        - GitHub repositories, source code, Python, libraries, frameworks, APIs, implementations

        General
        - Concept explanations, comparisons, advantages, disadvantages, use cases

        Questions:
        {sub_questions}

        Rules:
        1. A question may belong to multiple categories.
        2. Return ONLY a valid JSON array, no markdown, no explanation, no extra text.
        3. Output format:
        [
            {{"question": "...", "categories": ["Academic"], "priority": "Medium"}},
            {{"question": "...", "categories": ["Academic", "Coding"], "priority": "High"}}
        ]
        """

    content = ""
    try:
        response = llm.invoke(prompt)
        content = response.content
        if not isinstance(content, str):
            raise ValueError("Router did not return a string.")
        content = content.replace("```json", "").replace("```", "").strip()
        routes = json.loads(content)
    except Exception as e:
        print(f"\nROUTER ERROR: {e}")
        print(f"\nROUTER OUTPUT: {content}")
        return {
            "academic_questions": sub_questions,
            "coding_questions": sub_questions,
            "general_questions": sub_questions
        }

    academic_questions, coding_questions, general_questions = [], [], []

    for item in routes:
        question = item.get("question", "")
        categories = [c.lower() for c in item.get("categories", [])]

        matched = False
        if "academic" in categories:
            academic_questions.append(question)
            matched = True
        if "coding" in categories:
            coding_questions.append(question)
            matched = True
        if "general" in categories:
            general_questions.append(question)
            matched = True

        if not matched:
            general_questions.append(question)

    return {
        "academic_questions": academic_questions,
        "coding_questions": coding_questions,
        "general_questions": general_questions
    }