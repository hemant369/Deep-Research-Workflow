from backend.model.llm import llm


class SynthesizerAgent:
    def _format_evidence(self, evidence: list) -> str:
        if not evidence:
            return ""

        blocks = []
        max_sources = 18
        max_passages_per_source = 3

        # Prefer high-confidence sources, but keep coverage across the result set.
        sorted_evidence = sorted(
            evidence,
            key=lambda item: item.get("confidence", 0),
            reverse=True,
        )

        for item in sorted_evidence[:max_sources]:
            title = item.get("title", "Untitled")
            source_citation = item.get("citation", "")
            reference = item.get("reference", "")
            metadata = item.get("metadata", {})
            validation = metadata.get("validation", {})
            passages = metadata.get("passages", [])[:max_passages_per_source]

            if not passages:
                content = item.get("content", "")[:1200]
                passages = [{
                    "citation": source_citation,
                    "text": content,
                }]

            passage_lines = []
            for passage in passages:
                citation = passage.get("citation") or source_citation
                text = passage.get("text", "")
                if text:
                    passage_lines.append(f"- {citation} {text}")

            if not passage_lines:
                continue

            claims = validation.get("key_claims", [])
            claim_text = "; ".join(str(claim) for claim in claims[:4])

            blocks.append(
                "\n".join([
                    f"Source: {source_citation} {title}",
                    f"Reference: {reference}",
                    f"Validation: relevance={validation.get('relevance', '')}; support={validation.get('support', '')}",
                    f"Supported claims: {claim_text}",
                    "Passages:",
                    *passage_lines,
                ])
            )

        return "\n\n".join(blocks)

    def synthesize(self, query: str, evidence: list) -> str:
        evidence_text = self._format_evidence(evidence)

        if not evidence_text:
            return "No valid evidence found."

        prompt = f"""You are a research synthesis engine. Your job is to extract,
            deduplicate, and organize raw facts with enough detail for a full research report.

            Research topic:
            {query}

            Evidence:
            {evidence_text}

            Output ONLY this structure:

            FACTS:
            - <specific deduplicated fact with useful context> [passage_citation]
            - <specific deduplicated fact with useful context> [passage_citation]

            CONFLICTS:
            - <claim from source X> [passage_citation] vs <claim from source Y> [passage_citation]

            THEMES:
            - <common pattern or theme seen across multiple sources> [passage_citation][passage_citation]

            GAPS:
            - <something the query asks about that no evidence covers>

            Rules:
            - Every FACT must have at least one citation index.
            - Prefer passage citations such as [1.1] over source-only citations such as [1].
            - If two sources say the same thing, merge into one FACT and list both citations.
            - Use evidence from multiple sources instead of only the first few.
            - Do NOT invent anything.
            - Prefer 12-20 detailed FACTS when the evidence supports them.
            - Keep each bullet self-contained and informative.
            - Do NOT add any section beyond FACTS, CONFLICTS, THEMES, GAPS.
            """

        try:
            response = llm.invoke(prompt)
            content = response.content
            if not isinstance(content, str):
                content = str(content)
            return content.strip()
        except Exception as e:
            return f"Synthesis failed: {str(e)}"
