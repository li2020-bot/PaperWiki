import fitz


def extract_text(pdf_path: str) -> tuple:
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())

    text = "\n".join(pages)
    meta = doc.metadata or {}
    metadata = {
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
    }
    doc.close()
    return text, metadata
