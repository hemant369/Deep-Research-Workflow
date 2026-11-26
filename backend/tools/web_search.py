import logging
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests
from ddgs import DDGS

from core.config import settings
from schemas.tool_result import ToolResult, make_tool_result


logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DeepResearchAgent/1.0)"}
SKIP_TAGS = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg"}
TEXT_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "blockquote", "pre", "td"}
# Video and login-walled social hosts return no article text to plain HTTP scrapers.
SKIP_HOSTS = {
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "linkedin.com",
    "x.com",
    "twitter.com",
}


def _is_skipped_host(url: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.").removeprefix("m.")
    return any(host == blocked or host.endswith(f".{blocked}") for blocked in SKIP_HOSTS)


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
    if not url or _is_skipped_host(url):
        return ""
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=settings.page_fetch_timeout_seconds,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/plain" in content_type or "text/markdown" in content_type:
            text = " ".join(response.text.split())[:settings.max_page_chars]
            logger.info("Fetched plain text %s (%d chars)", url, len(text))
            return text
        if "html" not in content_type:
            return ""

        parser = _TextExtractor()
        parser.feed(response.text)
        text = "\n".join(parser.blocks)[:settings.max_page_chars]
        logger.info("Scraped %s (%d chars)", url, len(text))
        return text
    except Exception as exc:
        logger.info("Could not read %s: %s", url, exc)
        return ""


def search_web(query: str) -> list[ToolResult]:
    logger.info("DuckDuckGo search: %r", query)
    with DDGS() as ddgs:
        raw_hits = list(ddgs.text(query, max_results=settings.max_search_results + 4))

    # Drop video/social hosts so scrape slots go to readable articles and docs.
    hits = [hit for hit in raw_hits if not _is_skipped_host(hit.get("href", ""))]
    hits = (hits or raw_hits)[:settings.max_search_results]

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
    logger.info(
        "Web search returned %d result(s) (%d full pages) for %r",
        len(results),
        sum(1 for item in results if item["metadata"].get("full_page")),
        query,
    )
    return results
