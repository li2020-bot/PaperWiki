import os
import tempfile
import fitz
from paperwiki.pdf_extractor import extract_text


def _create_test_pdf(text: str) -> str:
    """Create a temporary PDF with given text for testing."""
    doc = fitz.open()
    doc.new_page()
    page = doc[0]
    page.insert_text((72, 72), text, fontsize=12)
    doc.set_metadata({"title": "Test Paper", "author": "Test Author"})
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    doc.save(tmp.name)
    doc.close()
    return tmp.name


def test_extract_text_basic():
    pdf_path = _create_test_pdf("This is a test paper about machine learning.")
    try:
        text, metadata = extract_text(pdf_path)
        assert "test paper" in text.lower()
        assert "machine learning" in text.lower()
        assert metadata["title"] == "Test Paper"
        assert metadata["author"] == "Test Author"
    finally:
        os.unlink(pdf_path)


def test_extract_text_multi_page():
    doc = fitz.open()
    for _ in range(3):
        doc.new_page()
        doc[-1].insert_text((72, 72), "Page content", fontsize=12)
    doc.set_metadata({"title": "Multi Page", "author": ""})
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    doc.save(tmp.name)
    doc.close()

    try:
        text, metadata = extract_text(tmp.name)
        assert text.count("Page content") == 3
        assert metadata["title"] == "Multi Page"
    finally:
        os.unlink(tmp.name)


def test_extract_text_empty_pdf():
    doc = fitz.open()
    doc.new_page()
    doc.set_metadata({"title": "", "author": ""})
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    doc.save(tmp.name)
    doc.close()

    try:
        text, metadata = extract_text(tmp.name)
        assert isinstance(text, str)
        assert isinstance(metadata, dict)
    finally:
        os.unlink(tmp.name)
