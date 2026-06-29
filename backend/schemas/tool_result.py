from typing import Any
from typing_extensions import NotRequired, TypedDict


class ToolResult(TypedDict):
    source: str
    title: str
    content: str
    url: str
    metadata: dict[str, Any]
    confidence: NotRequired[float]
    citation: NotRequired[str]
    reference: NotRequired[str]


def make_tool_result(
    *,
    source: str,
    title: str,
    content: str,
    url: str,
    metadata: dict[str, Any] | None = None,
    **extra: Any,
) -> ToolResult:
    result: ToolResult = {
        "source": str(source or ""),
        "title": str(title or ""),
        "content": str(content or ""),
        "url": str(url or ""),
        "metadata": metadata or {},
    }

    for key, value in extra.items():
        if value is not None:
            result[key] = value

    return result


def normalize_tool_result(item: Any) -> ToolResult:
    if not isinstance(item, dict):
        raise TypeError(f"Expected tool result dict, got {type(item).__name__}")

    metadata = item.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {"value": metadata}

    result = make_tool_result(
        source=item.get("source", ""),
        title=item.get("title", ""),
        content=item.get("content", item.get("body", "")),
        url=item.get("url", ""),
        metadata=metadata,
    )

    for key in ("confidence", "citation", "reference"):
        if key in item:
            result[key] = item[key]

    return result


def normalize_tool_results(payload: Any) -> list[ToolResult]:
    items = payload if isinstance(payload, list) else [payload]
    return [normalize_tool_result(item) for item in items]
