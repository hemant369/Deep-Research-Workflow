import json
from model.llm import llm

class PlannerAgent:

    def generate_sub_question(self, query):

        prompt = f"""You are an expert research planning assistant.
        Your job is to decompose a user's research query into 3–5 independent SEARCH QUERIES
        that will be sent directly to academic search engines, GitHub search, and web search.

        Query:
        {query}

        Step 1 — Identify the primary intent:
        Definition | Comparison | Survey | Tutorial | Implementation |
        Evaluation | Troubleshooting | Future Trends | Mixed

        Step 2 — Generate 3–5 search queries.

        Rules:
        - Each search query must be directly usable in arXiv, GitHub, or a web search.
        - Use concise keyword-based phrasing instead of conversational questions.
        - Remove filler words such as "what", "how", "can you", "please", "examples of".
        - Keep each query under 10 words.
        - Include important technical terms.
        - Each query should explore a different aspect of the original query.
        - Do not repeat information.

        Output ONLY valid JSON:
        {{
            "intent": "<detected intent>",
            "questions": [
                "<search query 1>",
                "<search query 2>",
                "<search query 3>"
            ]
        }}
        """

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