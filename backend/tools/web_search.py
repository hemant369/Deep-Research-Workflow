from ddgs import DDGS
from backend.schemas.tool_result import ToolResult, make_tool_result

def search_web(query: str) -> list[ToolResult]:
    result = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=5):
            result.append(
                make_tool_result(
                    source="ddgs",
                    title=item.get("title", ""),
                    content=item.get("body", ""),
                    url=item.get("href", ""),
                    metadata={}
                )
            )
    return result
