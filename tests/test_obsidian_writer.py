import os
import json
import tempfile
import hashlib
from paperwiki.obsidian_writer import ObsidianWriter


def test_sanitize_filename():
    w = ObsidianWriter("/tmp/vault", "wiki", "raw")
    assert w._sanitize_filename("Deep Learning: A Survey") == "Deep Learning_ A Survey"
    assert w._sanitize_filename("a/b:c*d?e\"f<g>h|i") == "a_b_c_d_e_f_g_h_i"


def test_save_report_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        writer = ObsidianWriter(vault, "wiki", "raw")
        writer.save_report(
            report_markdown="# Test Report\nContent here.",
            title="Test Paper Title",
            source_file="/tmp/test.pdf",
        )

        expected_dir = os.path.join(vault, "wiki")
        expected_file = os.path.join(expected_dir, "Test Paper Title.md")
        assert os.path.exists(expected_file)

        with open(expected_file, "r") as f:
            content = f.read()
        assert "# Test Report" in content
        assert "Content here." in content


def test_save_raw_text_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        writer = ObsidianWriter(vault, "wiki", "raw")
        writer.save_raw_text(
            raw_text="Raw paper text content.",
            title="Test Paper Title",
            source_file="/tmp/test.pdf",
        )

        expected_dir = os.path.join(vault, "wiki", "raw")
        expected_file = os.path.join(expected_dir, "Test Paper Title.md")
        assert os.path.exists(expected_file)

        with open(expected_file, "r") as f:
            content = f.read()
        assert "Raw paper text content." in content
        assert "# Test Paper Title" in content


def test_processed_files_tracking():
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        processed_path = os.path.join(tmp, "processed.json")
        writer = ObsidianWriter(vault, "wiki", "raw", processed_path)

        writer.save_report("# Report", "Paper One", "/tmp/paper1.pdf")

        with open(processed_path, "r") as f:
            data = json.load(f)
        assert "/tmp/paper1.pdf" in data
        assert "hash" in data["/tmp/paper1.pdf"]
        assert data["/tmp/paper1.pdf"]["output_file"] == "Paper One.md"


def test_is_processed():
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        processed_path = os.path.join(tmp, "processed.json")
        writer = ObsidianWriter(vault, "wiki", "raw", processed_path)

        assert not writer.is_processed("/tmp/nonexistent.pdf")

        writer.save_report("# Report", "Paper Test", "/tmp/paper.pdf")
        assert writer.is_processed("/tmp/paper.pdf")


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
