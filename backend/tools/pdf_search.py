from pypdf import PdfReader
from pathlib import Path
from backend.schemas.tool_result import ToolResult, make_tool_result


def search_pdf(file_path: str) -> ToolResult:
    reader = PdfReader(file_path)
    text = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text.strip())  # strip whitespace per page

    return make_tool_result(
        source="pdf",
        title=Path(file_path).stem,
        content="\n\n".join(text),           
        url=str(file_path),                  
        metadata={
            "num_pages": len(reader.pages),
            "extracted_pages": len(text)     
        }
    )
