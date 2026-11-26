import logging
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing_extensions import TypedDict

from mcp.server.fastmcp import FastMCP

from schemas.tool_result import ToolResult, normalize_tool_results
from tools.arxiv_search import search_arxiv
from tools.github_search import search_github
from tools.web_search import search_web


class SearchBatch(TypedDict):
    results: list[ToolResult]
    errors: list[dict[str, str]]


mcp = FastMCP("Deep Research")


def _search_many(
    queries: list[str],
    search: Callable[[str], list[ToolResult]],
) -> SearchBatch:
    """Run queries concurrently and keep successful results if one query fails."""
    clean_queries = [str(query).strip() for query in queries if str(query).strip()]
    results: list[ToolResult] = []
    errors: list[dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=min(len(clean_queries), 5) or 1) as executor:
        futures = {executor.submit(search, query): query for query in clean_queries}
        for future in as_completed(futures):
            query = futures[future]
            try:
                results.extend(normalize_tool_results(future.result()))
            except Exception as exc:
                errors.append(
                    {
                        "query": query,
                        "message": str(exc) or type(exc).__name__,
                    }
                )

    return {"results": results, "errors": errors}


@mcp.tool()
def web_search(queries: list[str]) -> SearchBatch:
    return _search_many(queries, search_web)


@mcp.tool()
def arxiv_search(
    queries: list[str],
) -> SearchBatch:
    return _search_many(queries, search_arxiv)


@mcp.tool()
def github_search(queries: list[str]) -> SearchBatch:
    return _search_many(queries, search_github)


if __name__ == "__main__":
    # Never write logs to stdout: MCP stdio transport uses stdout for JSON-RPC frames.
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(levelname)s [mcp] %(name)s: %(message)s",
    )
    mcp.run(transport="stdio")
