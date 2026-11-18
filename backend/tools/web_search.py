import logging
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

import requests
from ddgs import DDGS

from core.config import settings
from schemas.tool_result import ToolResult, make_tool_result


logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DeepResearchAgent/1.0)"}
SKIP_TAGS = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg"}
TEXT_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "blockquote", "pre", "td"}


class _TextExtractor(HTMLParser):
    """Collect readable text from content tags, skipping navigation and scripts."""

    def __init__(self):
        super().__init__()
        self.skip_depth = 0
        self.text_depth = 0
        self.blocks: list[str] = []
        self.current: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        elif tag in TEXT_TAGS:
            self.text_depth += 1

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        elif tag in TEXT_TAGS and self.text_depth:
            self.text_depth -= 1
            block = " ".join("".join(self.current).split())
            if len(block) > 40:
                self.blocks.append(block)
            self.current = []

    def handle_data(self, data):
        if self.text_depth and not self.skip_depth:
            self.current.append(data)


def fetch_page_text(url: str) -> str:
    """Download a web page and return its main text ('' if it cannot be read)."""
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=settings.page_fetch_timeout_seconds,
        )
        response.raise_for_status()
        if "html" not in response.headers.get("Content-Type", ""):
            return ""

        parser = _TextExtractor()
        parser.feed(response.text)
        return "\n".join(parser.blocks)[:settings.max_page_chars]
    except Exception as exc:
        logger.info("Could not read %s: %s", url, exc)
        return ""


def search_web(query: str) -> list[ToolResult]:
    with DDGS() as ddgs:
        hits = list(ddgs.text(query, max_results=settings.max_search_results))

    urls = [hit.get("href", "") for hit in hits[:settings.pages_per_query]]
    with ThreadPoolExecutor(max_workers=max(len(urls), 1)) as executor:
        pages = list(executor.map(fetch_page_text, urls))

    results = []
    for index, hit in enumerate(hits):
        snippet = hit.get("body", "")
        page_text = pages[index] if index < len(pages) else ""
        results.append(
            make_tool_result(
                source="ddgs",
                title=hit.get("title", ""),
                content=page_text or snippet,
                url=hit.get("href", ""),
                metadata={"snippet": snippet, "full_page": bool(page_text)},
            )
        )
    return results
