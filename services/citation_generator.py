from urllib.parse import urlparse

class CitationGenerator:
    def _domain(self, url: str) -> str:
        if not url:
            return "unknown"
        return urlparse(url).netloc

    def execute(self, results: list) -> list:
        citations = []
        for index, item in enumerate(results, start=1):
            citation_id = f"[{index}]"
            domain = self._domain(item.get("url", ""))
            title = item.get("title", "Untitled")
            url = item.get("url", "")

            item["citation"] = citation_id
            item["reference"] = f"{citation_id} {title} ({domain}) {url}"
            citations.append(item)

        print(f"CITATIONS: {len(citations)}")
        return citations
