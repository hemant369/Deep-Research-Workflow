import json
import re
from collections import Counter

from backend.model.llm import llm
from backend.schemas.tool_result import ToolResult


class EvidenceValidator:
    DOMAIN_SCORES = {
        "arxiv.org": 0.95,
        "pubmed.ncbi.nlm.nih.gov": 0.95,
        "scholar.google.com": 0.95,
        "github.com": 0.85,
        "docs.python.org": 0.90,
        "aws.amazon.com/documentation": 0.90,
        "cloud.google.com/docs": 0.90,
        "pytorch.org": 0.90,
        "huggingface.co": 0.88,
        "ibm.com": 0.88,
        "coursera.org": 0.85,
        "geeksforgeeks.org": 0.82,
        "wikipedia.org": 0.80,
        "stackoverflow.com": 0.75,
        "towardsdatascience.com": 0.70,
        "medium.com": 0.65,
        "linkedin.com": 0.50,
    }

    DEFAULT_SCORE = 0.60
    THRESHOLD = 0.65
    STOPWORDS = {
        "the", "and", "for", "with", "that", "this", "from", "what", "how",
        "are", "can", "into", "about", "using", "use", "why", "when", "where",
    }

    def _domain_score(self, url: str) -> float:
        for domain, score in self.DOMAIN_SCORES.items():
            if domain in url.lower():
                return score
        return self.DEFAULT_SCORE

    def _content_bonus(self, text: str) -> float:
        length = len(text)

        if length > 3000:
            return 0.10
        if length > 1500:
            return 0.08
        if length > 800:
            return 0.05
        if length > 300:
            return 0.02

        return 0.0

    def _title_bonus(self, title: str) -> float:
        return 0.03 if title.strip() else 0.0

    def _query_terms(self, query: str) -> set[str]:
        terms = {
            term
            for term in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", query.lower())
            if term not in self.STOPWORDS
        }
        return terms

    def _split_passages(self, text: str) -> list[str]:
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []

        chunks = re.split(r"(?<=[.!?])\s+", text)
        passages = []
        current = []
        current_len = 0

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            if current and current_len + len(chunk) > 700:
                passages.append(" ".join(current))
                current = []
                current_len = 0

            current.append(chunk)
            current_len += len(chunk)

        if current:
            passages.append(" ".join(current))

        return passages

    def _extract_passages(self, query: str, item: ToolResult, limit: int = 3) -> list[dict]:
        body = item.get("content", "")
        query_terms = self._query_terms(query)
        passages = self._split_passages(body)

        if not passages:
            return []

        scored = []
        for passage in passages:
            words = Counter(re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", passage.lower()))
            overlap = sum(words.get(term, 0) for term in query_terms)
            density = overlap / max(len(words), 1)
            score = overlap + density
            scored.append((score, passage))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        selected = [passage for score, passage in scored[:limit] if score > 0]

        if not selected:
            selected = passages[:limit]

        return [
            {
                "passage_id": "",
                "text": passage[:900],
            }
            for passage in selected
        ]

    def _llm_assessment(self, query: str, item: ToolResult, passages: list[dict]) -> dict:
        title = item.get("title", "")
        passage_text = "\n\n".join(
            f"- {passage['text']}"
            for passage in passages
        )[:3000]

        prompt = f"""
        You are validating whether evidence supports answering a research query.

        Query:
        {query}

        Source title:
        {title}

        Candidate passages:
        {passage_text}

        Return ONLY valid JSON:
        {{
          "relevance": "Relevant | Partially Relevant | Irrelevant",
          "support": "Strong | Moderate | Weak",
          "key_claims": ["claim directly supported by the passages"],
          "rationale": "short reason"
        }}
        """

        try:
            response = llm.invoke(prompt)
            content = str(response.content).replace("```json", "").replace("```", "").strip()
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("Assessment was not an object.")
            return data
        except Exception:
            return {
                "relevance": "Partially Relevant" if passages else "Irrelevant",
                "support": "Moderate" if passages else "Weak",
                "key_claims": [],
                "rationale": "Fallback assessment based on extracted passages.",
            }

    def _assessment_bonus(self, assessment: dict) -> float:
        relevance = str(assessment.get("relevance", "")).lower()
        support = str(assessment.get("support", "")).lower()

        bonus = 0.0
        if relevance.startswith("relevant"):
            bonus += 0.10
        elif "partial" in relevance:
            bonus += 0.05

        if support.startswith("strong"):
            bonus += 0.08
        elif support.startswith("moderate"):
            bonus += 0.04

        return bonus

    def execute(self, query: str, results: list[ToolResult]) -> list[ToolResult]:
        validated: list[ToolResult] = []

        for item in results:
            url = item.get("url", "")
            title = item.get("title", "")
            body = item.get("content", "")
            passages = self._extract_passages(query, item)
            assessment = self._llm_assessment(query, item, passages)

            score = self._domain_score(url)
            score += self._content_bonus(body)
            score += self._title_bonus(title)
            score += self._assessment_bonus(assessment)
            score = min(score, 1.0)

            metadata = item.setdefault("metadata", {})
            metadata["validation"] = {
                "relevance": assessment.get("relevance", ""),
                "support": assessment.get("support", ""),
                "key_claims": assessment.get("key_claims", []),
                "rationale": assessment.get("rationale", ""),
            }
            metadata["passages"] = passages
            item["confidence"] = round(score, 2)

            if score >= self.THRESHOLD:
                validated.append(item)

        print(
            f"VALIDATOR: {len(results)} -> {len(validated)} "
            f"(threshold={self.THRESHOLD})"
        )

        return validated
