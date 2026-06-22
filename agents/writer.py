from model.llm import llm


class WriterAgent:

    def generate_report(self, query, synthesized_text):

        prompt = f"""
            You are a professional research writer.

            Original Topic:
            {query}

            Research Findings:
            {synthesized_text}

            Instructions:
            - Write a structured report.
            - Add an Introduction.
            - Add Key Findings sections.
            - Add a Conclusion.
            - Keep it concise.
            - Use headings.
            """

        response = llm.invoke(prompt)

        return response.content