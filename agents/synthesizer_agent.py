from model.llm import llm

class SynthesizerAgent:
    def synthesize(self, query: str, evidence: list) -> str:
        if not evidence:
            return "No evidence provided for synthesis."

        formatted_evidence = []
        total_chars = 0
        MAX_CHARS = 12000

        for i, item in enumerate(evidence):
            title = item.get("title", "Untitled")
            body = item.get("body", "") or item.get("content", "")
            citation = item.get("citation", f"Source {i+1}")

            if not body:
                continue

            block = f"[{i+1}] Title: {title}\nEvidence: {body}\nCitation: {citation}\n"

            if total_chars + len(block) > MAX_CHARS:
                break

            formatted_evidence.append(block)
            total_chars += len(block)

        if not formatted_evidence:
            return "No valid evidence found."

        evidence_text = "\n".join(formatted_evidence)

        prompt = f"""You are a research synthesis engine. Your ONLY job is to extract, 
            deduplicate, and organize raw facts. Do NOT write prose. Do NOT create headings or 
            sections. Do NOT format for readability. A Writer agent will handle all of that.

            Research topic:
            {query}

            Evidence:
            {evidence_text}

            Output ONLY this flat structure:

            FACTS:
            - <single deduplicated fact> [citation_index]
            - <single deduplicated fact> [citation_index]

            CONFLICTS:
            - <claim from source X> [X] vs <claim from source Y> [Y]

            THEMES:
            - <common pattern or theme seen across multiple sources> [X][Y]

            GAPS:
            - <something the query asks about that no evidence covers>

            Rules:
            - Every FACT must have at least one citation index
            - If two sources say the same thing, merge into one FACT, list both citations 
            - Do NOT invent anything
            - Do NOT write sentences or paragraphs
            - Do NOT add any section beyond FACTS, CONFLICTS, THEMES, GAPS
            """

        try:
            response = llm.invoke(prompt)
            content = response.content
            if not isinstance(content, str):
                content = str(content)
            return content.strip()
        except Exception as e:
            return f"Synthesis failed: {str(e)}"