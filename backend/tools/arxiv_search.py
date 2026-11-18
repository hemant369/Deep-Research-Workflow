import re
import arxiv

from core.config import settings
from schemas.tool_result import ToolResult, make_tool_result


STOPWORDS = {"the", "and", "for", "with", "how", "what", "why", "does", "from", "into", "over"}


def _build_arxiv_query(query: str) -> str:
    """Require all meaningful keywords to match in title or abstract (AND instead of arXiv's default OR)."""
    terms = [
        word for word in re.findall(r"[A-Za-z0-9-]+", query)
        if len(word) > 2 and word.lower() not in STOPWORDS
    ]
    if not terms:
        return query
    return " AND ".join(f"all:{term}" for term in terms[:6])


def search_arxiv(query: str) -> list[ToolResult]:
    """Search arXiv and return paper abstracts."""
    search = arxiv.Search(
        query=_build_arxiv_query(query),
        max_results=settings.max_search_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    return [
        make_tool_result(
            source="arxiv",
            title=paper.title,
            content=paper.summary,
            url=paper.entry_id,
            metadata={
                "authors": [author.name for author in paper.authors],
                "published": paper.published.strftime("%Y-%m-%d"),
                "categories": paper.categories,
                "journal_ref": paper.journal_ref or "",
                "doi": paper.doi or "",
            },
        )
        for paper in arxiv.Client().results(search)
    ]
