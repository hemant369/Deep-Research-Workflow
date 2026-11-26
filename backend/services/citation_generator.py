import re
from urllib.parse import urlparse

from schemas.tool_result import ToolResult


CITATION_PATTERN = re.compile(r"\[(\d+)(?:\.(\d+))?\](?!\()")


class CitationGenerator:
    """Assign hierarchical [source] / [source.passage] IDs and verify report citations."""

    def _domain(self, url: str) -> str:
        if not url:
            return "unknown"
        return urlparse(url).netloc

    def execute(self, results: list[ToolResult]) -> list[ToolResult]:
        citations: list[ToolResult] = []
        for source_index, item in enumerate(results, start=1):
            citation_id = f"[{source_index}]"
            domain = self._domain(item.get("url", ""))
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            metadata = item.setdefault("metadata", {})
            passages = metadata.get("passages", [])

            for passage_index, passage in enumerate(passages, start=1):
                passage["passage_id"] = f"{source_index}.{passage_index}"
                passage["citation"] = f"[{source_index}.{passage_index}]"

            item["citation"] = citation_id
            item["reference"] = f"{citation_id} {title} ({domain}) {url}"
            metadata["passage_references"] = [
                f"[{passage['passage_id']}] {passage['text']}"
                for passage in passages
                if passage.get("passage_id") and passage.get("text")
            ]
            citations.append(item)

        return citations

    def format_references(
        self,
        results: list[ToolResult],
        cited: set[int] | None = None,
    ) -> str:
        return "\n".join(
            f"- {item.get('reference', '')}"
            for index, item in enumerate(results, start=1)
            if item.get("reference") and (not cited or index in cited)
        )

    def remove_unknown_citations(self, report: str, results: list[ToolResult]) -> str:
        """Drop citation markers like [7] or [7.2] that point to no real source/passage."""
        valid: set[str] = set()
        for source_index, item in enumerate(results, start=1):
            valid.add(str(source_index))
            for passage in item.get("metadata", {}).get("passages", []):
                if passage.get("passage_id"):
                    valid.add(passage["passage_id"])

        def replace(match: re.Match) -> str:
            key = match.group(1) if match.group(2) is None else f"{match.group(1)}.{match.group(2)}"
            return match.group(0) if key in valid else ""

        return CITATION_PATTERN.sub(replace, report)

    def finalize_report(self, report: str, results: list[ToolResult]) -> tuple[str, bool]:
        """Scrub invalid citation markers and append `# References` for cited sources only."""
        cleaned = self.remove_unknown_citations(report, results)
        had_unknown = cleaned != report
        cited = {int(match.group(1)) for match in CITATION_PATTERN.finditer(cleaned)}
        cited_references = self.format_references(results, cited)
        body = re.split(r"(?im)^# References\s*$", cleaned, maxsplit=1)[0].rstrip()
        return f"{body}\n\n# References\n{cited_references}".strip(), had_unknown
