import arxiv
from schemas.tool_result import ToolResult

def search_arxiv(query: str):
    papers = []
    client = arxiv.Client()

    search = arxiv.Search(
        query=query,
        max_results=5
    )

    for paper in client.results(search):
        papers.append(
            ToolResult(
                source="arxiv",
                title=paper.title,
                content=paper.summary,
                url=paper.entry_id,
                metadata={
                    "authors": [author.name for author in paper.authors],
                    "published": paper.published.strftime("%Y-%m-%d"),
                    "updated": paper.updated.strftime("%Y-%m-%d"),
                    "categories": paper.categories,
                    "comment": paper.comment or "",
                    "journal_ref": paper.journal_ref or "",
                    "doi": paper.doi or ""
                }
            )
        )
    return papers