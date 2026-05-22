import fitz


def extract_text(pdf_path: str) -> tuple[str, dict]:
    with fitz.open(pdf_path) as doc:
        pages = [page.get_text() for page in doc]
        text = "\n".join(pages)
        meta = doc.metadata or {}
        metadata = {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
        }
    return text, metadata
