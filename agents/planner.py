import json
from model.llm import llm

class PlannerAgent:

    def generate_sub_question(self, query):

        prompt = f"""You are a research planning assistant.

        Given a research query, decompose it into focused sub-questions that can be 
        independently searched across academic papers, code repositories, and the web.

        Query: {query}

        Rules:
        1. Generate 3 to 5 sub-questions — no more, no less.
        2. Each sub-question must be self-contained and searchable on its own.
        3. Cover different angles: definitions, comparisons, implementations, limitations, recent developments.
        4. Do NOT repeat or rephrase the original query as a sub-question.
        5. Do NOT add explanations or commentary.
        6. Return ONLY a valid JSON array of strings.

        Return the sub-questions as a JSON array."""

        response = llm.invoke(prompt)
        content = response.content

        if isinstance(content, list):
            content = " ".join(
                item if isinstance(item, str) else json.dumps(item)
                for item in content
            )
        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

        try:
            return json.loads(content)
        except Exception as e:
            return [content]