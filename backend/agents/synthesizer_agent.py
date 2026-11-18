from model.llm import llm
from schemas.tool_result import ToolResult


class SynthesizerAgent:
    def _format_evidence(self, evidence: list[ToolResult]) -> str:
        """Format validated passages for the synthesis prompt."""
        sources: list[str] = []

        for item in evidence:
            passages = item.get("metadata", {}).get("passages", [])
            passage_lines = [
                f"- {passage.get('citation', item.get('citation', ''))} "
                f"{passage.get('text', '')}"
                for passage in passages
                if passage.get("text")
            ]

            if passage_lines:
                title = item.get("title", "Untitled")
                url = item.get("url", "")
                sources.append(f"Source: {title} ({url})\n" + "\n".join(passage_lines))

        return "\n\n".join(sources)

    async def synthesize(
        self,
        query: str,
        evidence: list[ToolResult],
    ) -> str:
        evidence_text = self._format_evidence(evidence)
        if not evidence_text:
            return "No valid evidence found."

        prompt = f"""Summarize the evidence for this research question:

{query}

Evidence:
{evidence_text}

Rules:
1. Use ONLY the supplied evidence and preserve citation numbers like [1.1] or [2.3] exactly.
2. Do NOT attribute findings from a general academic paper to a specific company, product, or author in the query unless that source explicitly mentions them by name. If a source only provides general industry/scientific context, label it clearly as general context or omit it if it does not answer the query.
3. Under GAPS, list specific technical sub-questions from the user's query that are still missing concrete evidence.

Return only these sections:

FACTS:
- Important findings with their citation numbers.

CONFLICTS:
- Claims where sources disagree or evidence is uncertain.

GAPS:
- Parts of the question not answered by the evidence.
"""

        response = await llm.ainvoke(prompt)
        return str(response.content).strip()
