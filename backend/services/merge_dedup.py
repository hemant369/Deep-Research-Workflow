from schemas.tool_result import ToolResult


def result_key(result: ToolResult) -> str:
    """Identity of a source: normalized URL, or title when no URL exists."""
    url = result.get("url", "").strip().lower().rstrip("/")
    return url or result.get("title", "").strip().lower()


def remove_duplicates(results: list[ToolResult]) -> list[ToolResult]:
    """Keep the first result for each URL, or title when no URL exists."""
    unique_results: list[ToolResult] = []
    seen: set[str] = set()

    for result in results:
        key = result_key(result)
        if not key or key in seen:
            continue

        seen.add(key)
        unique_results.append(result)

    return unique_results
