from urllib.parse import urlparse

from backend.schemas.tool_result import ToolResult


class CitationGenerator:
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

        print(f"CITATIONS: {len(citations)}")
        return citations
