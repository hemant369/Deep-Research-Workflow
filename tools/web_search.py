from ddgs import DDGS
from schemas.tool_result import ToolResult

def search_web(query: str):
    result = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=5):
            result.append(
                ToolResult(
                    source="ddgs",
                    title= item.get("title", ""),
                    content=item.get("body", ""),
                    url=item.get("href", ""),
                    metadata={}
                )
            )
    return result