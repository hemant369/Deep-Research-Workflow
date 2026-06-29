from urllib.parse import urlparse
import re
from backend.schemas.tool_result import ToolResult

class MergeDedup:
    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        normalized = parsed.netloc + parsed.path.rstrip("/")
        normalized = re.sub(r"v\d+$", "", normalized)
        return normalized.lower()

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower().replace("\n", " ")
        text = " ".join(text.split())
        return text.strip()

    def execute(self, results: list[ToolResult]) -> list[ToolResult]:
        unique_results: list[ToolResult] = []
        seen_urls, seen_titles, seen_bodies = set(), set(), set()

        for item in results:
            url = item.get("url", "")
            title = self._normalize_text(item.get("title", ""))
            body = self._normalize_text(
                item.get("body", "")
                or item.get("content", "")
                or item.get("description", "")
            )

            normalized_url = self._normalize_url(url) if url else ""

            duplicate = (
                (normalized_url and normalized_url in seen_urls)
                or (title and title in seen_titles)
                or (body and body in seen_bodies)
            )

            if duplicate:
                continue

            if normalized_url:
                seen_urls.add(normalized_url)
            if title:
                seen_titles.add(title)
            if body:
                seen_bodies.add(body)

            unique_results.append(item)

        print(f"MERGE: {len(results)} -> {len(unique_results)}")
        return unique_results
