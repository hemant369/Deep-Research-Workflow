from urllib.parse import urlparse

class MergeDedup:

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        # strip scheme, trailing slashes, query params, fragments
        normalized = parsed.netloc + parsed.path.rstrip("/")
        # strip arxiv version suffixes (v1, v2, v3...)
        import re
        normalized = re.sub(r"v\d+$", "", normalized)
        return normalized.lower()

    def execute(self, results: list) -> list:
        unique_results = []
        seen_urls = set()
        seen_titles = set()

        for item in results:
            url = item.get("url", "")
            title = item.get("title", "").strip().lower()

            if not url:
                continue

            normalized = self._normalize_url(url)

            # deduplicate by both normalized URL and exact title
            if normalized in seen_urls or (title and title in seen_titles):
                continue

            seen_urls.add(normalized)
            if title:
                seen_titles.add(title)

            unique_results.append(item)

        return unique_results