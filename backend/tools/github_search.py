import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import settings
from schemas.tool_result import ToolResult, make_tool_result


logger = logging.getLogger(__name__)
MAX_README_REPOS = 2
MAX_README_CHARS = 4000


def _fetch_readme(session: requests.Session, full_name: str, headers: dict[str, str]) -> str:
    """Fetch raw README text for a repository, returning '' if unavailable."""
    if not full_name:
        return ""
    try:
        readme_headers = {**headers, "Accept": "application/vnd.github.raw+json"}
        resp = session.get(
            f"https://api.github.com/repos/{full_name}/readme",
            headers=readme_headers,
            timeout=settings.page_fetch_timeout_seconds,
        )
        if resp.status_code == 200 and resp.text:
            return resp.text.strip()[:MAX_README_CHARS]
    except Exception:
        pass
    return ""


def search_github(query: str) -> list[ToolResult]:
    logger.info("GitHub search: %r", query)
    url = "https://api.github.com/search/repositories"

    params = {
        "q": query,
        "sort": "stars",
        "per_page": settings.max_search_results,
    }

    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    retry = Retry(
        total=settings.http_max_retries,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )

    results: list[ToolResult] = []
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter(max_retries=retry))
        response = session.get(
            url,
            params=params,
            headers=headers,
            timeout=settings.http_timeout_seconds,
        )
        response.raise_for_status()
        items = response.json().get("items", [])

        for index, repo in enumerate(items):
            full_name = repo.get("full_name", "")
            description = repo.get("description", "") or ""
            readme = _fetch_readme(session, full_name, headers) if index < MAX_README_REPOS else ""
            content = f"{description}\n\n{readme}".strip() if readme else description

            results.append(
                make_tool_result(
                    source="github",
                    title=full_name or repo.get("name", ""),
                    content=content,
                    url=repo.get("html_url", ""),
                    metadata={
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "language": repo.get("language", "") or "",
                        "has_readme": bool(readme),
                    },
                )
            )

    logger.info(
        "GitHub returned %d repo(s) (%d with README) for %r",
        len(results),
        sum(1 for item in results if item["metadata"].get("has_readme")),
        query,
    )
    return results
