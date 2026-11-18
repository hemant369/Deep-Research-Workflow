import json
import logging
import re

from core.config import settings
from model.llm import llm
from schemas.tool_result import ToolResult


logger = logging.getLogger(__name__)

CONFIDENCE = {
    "relevant": 0.9,
    "partially relevant": 0.7,
}


class EvidenceValidator:
    def _query_terms(self, query: str) -> set[str]:
        return {word for word in re.findall(r"\w+", query.lower()) if len(word) > 3}

    def _extract_passages(self, content: str, query: str = "", limit: int = 5) -> list[dict]:
        """Split content into ~700-char passages and keep the ones most related to the query."""
        sentences = re.split(r"(?<=[.!?])\s+", " ".join(content.split()))
        passages: list[str] = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) > 700 and current:
                passages.append(current)
                current = ""
            current = f"{current} {sentence}".strip()

        if current:
            passages.append(current)

        terms = self._query_terms(query)
        scored = [
            (sum(passage.lower().count(term) for term in terms), index)
            for index, passage in enumerate(passages)
        ]
        best = sorted(scored, key=lambda pair: (-pair[0], pair[1]))[:limit]
        selected = sorted(index for _, index in best)

        return [
            {"passage_id": "", "text": passages[index]}
            for index in selected
        ]

    def _parse_assessments(self, content: str) -> dict[int, dict]:
        """Parse the model's JSON array, skipping malformed entries instead of failing."""
        start, end = content.find("["), content.rfind("]")
        if start == -1 or end <= start:
            raise ValueError("Validator response contains no JSON array.")

        data = json.loads(content[start:end + 1])
        assessments: dict[int, dict] = {}
        for item in data if isinstance(data, list) else []:
            if not isinstance(item, dict):
                continue
            try:
                assessments[int(item["id"])] = item
            except (KeyError, TypeError, ValueError):
                continue
        return assessments

    async def _assess_batch(
        self,
        query: str,
        batch: list[tuple[int, ToolResult, list[dict]]],
    ) -> dict[int, dict]:
        candidates = [
            {
                "id": item_id,
                "source": item.get("source", ""),
                "title": item.get("title", ""),
                "passages": [passage["text"] for passage in passages],
            }
            for item_id, item, passages in batch
        ]

        prompt = f"""Judge whether each candidate source directly helps answer the research query.

Query: {query}
Sources: {json.dumps(candidates)[:40000]}

Strict Filtering Rules:
1. Mark a source "Irrelevant" if it is off-topic, about a homonym in another field (e.g. the TESLA particle accelerator instead of Tesla vehicles), or unrelated to the core subject of the query.
2. Mark a source "Relevant" ONLY if it directly addresses both the main subject/entity and the technical topic of the query.
3. Mark a source "Partially Relevant" ONLY if it provides directly applicable technical evidence for part of the query.

Return ONLY a JSON array containing one object per source ID:
[
  {{
    "id": 0,
    "relevance": "Relevant | Partially Relevant | Irrelevant",
    "support": "Strong | Moderate | Weak",
    "key_claims": ["claim"],
    "rationale": "short explanation"
  }}
]
"""
        try:
            response = await llm.ainvoke(prompt)
            return self._parse_assessments(str(response.content))
        except Exception:
            logger.warning("Validator could not assess a batch.")
            return {}

    async def execute(
        self,
        query: str,
        results: list[ToolResult],
    ) -> list[ToolResult]:
        candidates = results[:settings.max_evidence_results]
        prepared = [
            (index, item, self._extract_passages(item.get("content", ""), query))
            for index, item in enumerate(candidates)
            if item.get("content", "").strip()
        ]

        assessments: dict[int, dict] = {}
        for start in range(0, len(prepared), settings.validation_batch_size):
            batch = prepared[start:start + settings.validation_batch_size]
            assessments.update(await self._assess_batch(query, batch))

        validated: list[ToolResult] = []
        for item_id, item, passages in prepared:
            if not passages:
                continue

            assessment = assessments.get(item_id)
            if not assessment:
                continue

            relevance = str(assessment.get("relevance", "")).strip().lower()
            confidence = CONFIDENCE.get(relevance)
            if confidence is None:
                continue

            metadata = item.setdefault("metadata", {})
            metadata["validation"] = assessment
            metadata["passages"] = passages
            item["confidence"] = confidence
            validated.append(item)

        return validated
