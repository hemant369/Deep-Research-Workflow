import json
from model.llm import llm

class PlannerAgent:

    def generate_sub_question(self, query):

        prompt = f"""Given the query: '{query}', break it down into smaller, 
        more specific sub-questions that can help in finding the answer. 
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