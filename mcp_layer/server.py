from mcp.server.fastmcp import FastMCP
from dataclasses import asdict
from tools.web_search import search_web
from tools.arxiv_search import search_arxiv
from tools.github_search import search_github
from tools.pdf_search import search_pdf

mcp = FastMCP(
    "Deep Research",
)

@mcp.tool()
def web_search(query: str):
    print(f"MCP TOOL CALLED -> {query}")
    results = search_web(query)
    return [asdict(r) for r in results]  

@mcp.tool()
def arxiv_search(query: str):
    print(f"MCP TOOL CALLED -> {query}")
    results = search_arxiv(query)
    return [asdict(r) for r in results]

@mcp.tool()
def github_search(query: str):
    print(f"MCP TOOL CALLED -> {query}")
    results = search_github(query)
    return [asdict(r) for r in results]

@mcp.tool()
def pdf_search(file_path: str):
    print(f"MCP TOOL CALLED -> {file_path}")
    result = search_pdf(file_path)
    return asdict(result)  # single result, not a list

if __name__ == "__main__":
    mcp.run(transport="stdio") 