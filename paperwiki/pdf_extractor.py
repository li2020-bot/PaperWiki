import fitz


def extract_pdf_text(pdf_path: str) -> str:
    """Extract plain text from a PDF using pymupdf's text extraction.

    Returns the full text of all pages joined with double newlines.
    """
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        text = page.get_text("text").strip()
        if text:
            pages.append(text)
    doc.close()
    return "\n\n".join(pages)


def extract_text(pdf_path: str) -> tuple[str, dict]:
    """Extract text and metadata from a PDF (backward-compatible interface).

    Returns (text, metadata) where text is plain text of all pages
    and metadata is a dict with title, author, page_count, etc.
    """
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        text = page.get_text("text").strip()
        if text:
            pages.append(text)
    meta = doc.metadata or {}
    metadata = {
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
        "page_count": doc.page_count,
    }
    doc.close()
    return "\n\n".join(pages), metadata
