import arxiv
import requests
from io import BytesIO
from pypdf import PdfReader
from backend.schemas.tool_result import ToolResult, make_tool_result


MAX_PDF_PAGES = 8
MAX_PDF_CHARS = 18000
REQUEST_TIMEOUT = 20


def _extract_pdf_text(pdf_url: str) -> tuple[str, dict]:
    metadata = {
        "pdf_url": pdf_url,
        "pdf_extracted": False,
        "pdf_pages_read": 0,
        "pdf_error": "",
    }

    if not pdf_url:
        metadata["pdf_error"] = "No PDF URL available."
        return "", metadata

    try:
        response = requests.get(pdf_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        reader = PdfReader(BytesIO(response.content))
        chunks = []

        page_count = min(len(reader.pages), MAX_PDF_PAGES)
        for page_number in range(page_count):
            page = reader.pages[page_number]
            page_text = page.extract_text()
            if not page_text:
                continue

            chunks.append(page_text.strip())
            metadata["pdf_pages_read"] = page_number + 1

            if sum(len(chunk) for chunk in chunks) >= MAX_PDF_CHARS:
                break

        text = "\n\n".join(chunks).strip()[:MAX_PDF_CHARS]
        metadata["pdf_extracted"] = bool(text)

        if not text:
            metadata["pdf_error"] = "PDF downloaded, but no text could be extracted."

        return text, metadata
    except Exception as e:
        metadata["pdf_error"] = str(e)
        return "", metadata


def search_arxiv(
    query: str,
    include_pdf: bool = True,
    max_results: int = 5,
    max_pdf_results: int = 2,
) -> list[ToolResult]:
    papers = []
    client = arxiv.Client()

    search = arxiv.Search(
        query=query,
        max_results=max_results
    )

    for index, paper in enumerate(client.results(search)):
        pdf_text = ""
        pdf_metadata = {
            "pdf_url": getattr(paper, "pdf_url", ""),
            "pdf_extracted": False,
            "pdf_pages_read": 0,
            "pdf_error": "PDF extraction disabled.",
        }

        if include_pdf and index < max_pdf_results:
            pdf_text, pdf_metadata = _extract_pdf_text(getattr(paper, "pdf_url", ""))
        elif include_pdf:
            pdf_metadata["pdf_error"] = "PDF extraction skipped after max_pdf_results."

        content_parts = [
            f"Abstract:\n{paper.summary}"
        ]

        if pdf_text:
            content_parts.append(
                f"Extracted PDF text from first {pdf_metadata['pdf_pages_read']} pages:\n{pdf_text}"
            )

        papers.append(
            make_tool_result(
                source="arxiv",
                title=paper.title,
                content="\n\n".join(content_parts),
                url=paper.entry_id,
                metadata={
                    "authors": [author.name for author in paper.authors],
                    "published": paper.published.strftime("%Y-%m-%d"),
                    "updated": paper.updated.strftime("%Y-%m-%d"),
                    "categories": paper.categories,
                    "comment": paper.comment or "",
                    "journal_ref": paper.journal_ref or "",
                    "doi": paper.doi or "",
                    **pdf_metadata,
                }
            )
        )
    return papers
