from mcp.server.fastmcp import FastMCP
from backend.tools.web_search import search_web
from backend.tools.arxiv_search import search_arxiv
from backend.tools.github_search import search_github
from backend.tools.pdf_search import search_pdf
from backend.schemas.tool_result import ToolResult, normalize_tool_results

mcp = FastMCP(
    "Deep Research",
)

@mcp.tool()
def web_search(query: str) -> list[ToolResult]:
    print(f"MCP TOOL CALLED -> {query}")
    results = search_web(query)
    return normalize_tool_results(results)

@mcp.tool()
def arxiv_search(
    query: str,
    include_pdf: bool = True,
    max_results: int = 5,
    max_pdf_results: int = 2,
) -> list[ToolResult]:
    print(f"MCP TOOL CALLED -> {query}")
    results = search_arxiv(
        query,
        include_pdf=include_pdf,
        max_results=max_results,
        max_pdf_results=max_pdf_results
    )
    return normalize_tool_results(results)

@mcp.tool()
def github_search(query: str) -> list[ToolResult]:
    print(f"MCP TOOL CALLED -> {query}")
    results = search_github(query)
    return normalize_tool_results(results)

@mcp.tool()
def pdf_search(file_path: str) -> list[ToolResult]:
    print(f"MCP TOOL CALLED -> {file_path}")
    result = search_pdf(file_path)
    return normalize_tool_results(result)

if __name__ == "__main__":
    mcp.run(transport="stdio") 
