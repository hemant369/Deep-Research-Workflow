class SynthesizerAgent:

    def synthesize(self, query: str, evidence):

        synthesized_text = ""

        seen = set()

        for item in evidence:

            body = item.get("body", "").strip()

            if not body:

                continue

            if body in seen:

                continue

            seen.add(body)

            citation = item.get("citation", "")

            synthesized_text += (

                f"{body} {citation}\n\n"

            )

        return synthesized_text