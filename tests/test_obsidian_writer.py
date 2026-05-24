import os
import json
import tempfile
from paperwiki.obsidian_writer import ObsidianWriter


def _temp_pdf(dir_path: str, filename: str, content: bytes = b"pdf content") -> str:
    pdf_path = os.path.join(dir_path, filename)
    with open(pdf_path, "wb") as f:
        f.write(content)
    return pdf_path


def test_sanitize_filename():
    w = ObsidianWriter("/tmp/vault", "wiki")
    assert w._sanitize_filename("Deep Learning: A Survey") == "Deep Learning_ A Survey"
    assert w._sanitize_filename("a/b:c*d?e\"f<g>h|i") == "a_b_c_d_e_f_g_h_i"


def test_save_report_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        source_file = _temp_pdf(tmp, "test.pdf")
        writer = ObsidianWriter(vault, "wiki")
        writer.save_report(
            report_markdown="# Test Report\nContent here.",
            title="Test Paper Title",
            source_file=source_file,
        )

        expected_dir = os.path.join(vault, "wiki")
        expected_file = os.path.join(expected_dir, "Test Paper Title.md")
        assert os.path.exists(expected_file)

        with open(expected_file, "r") as f:
            content = f.read()
        assert "# Test Report" in content
        assert "Content here." in content


def test_processed_files_tracking():
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        processed_path = os.path.join(tmp, "processed.json")
        source_file = _temp_pdf(tmp, "paper1.pdf")
        writer = ObsidianWriter(vault, "wiki", processed_path)

        writer.save_report("# Report", "Paper One", source_file)

        with open(processed_path, "r") as f:
            data = json.load(f)
        assert source_file in data
        assert "hash" in data[source_file]
        assert data[source_file]["output_file"] == "Paper One.md"


def test_is_processed():
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        processed_path = os.path.join(tmp, "processed.json")
        source_file = _temp_pdf(tmp, "paper.pdf")
        writer = ObsidianWriter(vault, "wiki", processed_path)

        assert not writer.is_processed(source_file)

        writer.save_report("# Report", "Paper Test", source_file)
        assert writer.is_processed(source_file)


def test_hash_calculation():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"test pdf content 123")
        tmp_path = f.name

    try:
        h1 = ObsidianWriter._file_hash(tmp_path)
        h2 = ObsidianWriter._file_hash(tmp_path)
        assert h1 == h2
        assert isinstance(h1, str)
        assert len(h1) == 64
    finally:
        os.unlink(tmp_path)
