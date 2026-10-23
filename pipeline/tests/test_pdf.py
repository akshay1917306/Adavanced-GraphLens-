import pytest
from pypdf import PdfWriter

from graphlens_pipeline import pdf
from graphlens_pipeline.errors import IngestError
from tests.conftest import make_text_pdf


def test_reads_text_from_a_real_pdf(tmp_path):
    path = tmp_path / "ok.pdf"
    lines = [f"Line {i} of a small test paper about retrieval and answers." for i in range(30)]
    make_text_pdf(path, lines)
    pages = pdf.extract_pages(path)
    assert len(pages) == 1
    assert "Line 0 of a small test paper" in pages[0]
    assert "Line 29" in pages[0]


def test_missing_file(tmp_path):
    with pytest.raises(IngestError, match="missing"):
        pdf.extract_pages(tmp_path / "nope.pdf")


def test_empty_file(tmp_path):
    path = tmp_path / "empty.pdf"
    path.write_bytes(b"")
    with pytest.raises(IngestError, match="empty"):
        pdf.extract_pages(path)


def test_not_a_pdf(tmp_path):
    path = tmp_path / "fake.pdf"
    path.write_bytes(b"This is plain text, not a PDF.")
    with pytest.raises(IngestError, match="not a PDF"):
        pdf.extract_pages(path)


def test_corrupt_pdf(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.4\n1 0 obj\n<< garbage that never ends")
    with pytest.raises(IngestError, match="could not be read"):
        pdf.extract_pages(path)


def test_pdf_without_text(tmp_path):
    path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with path.open("wb") as handle:
        writer.write(handle)
    with pytest.raises(IngestError, match="no extractable text"):
        pdf.extract_pages(path)


def test_file_too_large(tmp_path, monkeypatch):
    path = tmp_path / "big.pdf"
    make_text_pdf(path, ["x" * 80] * 20)
    monkeypatch.setattr(pdf, "MAX_PDF_BYTES", 100)
    with pytest.raises(IngestError, match="larger than"):
        pdf.extract_pages(path)


def test_too_many_pages(tmp_path, monkeypatch):
    path = tmp_path / "many.pdf"
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=200, height=200)
    with path.open("wb") as handle:
        writer.write(handle)
    monkeypatch.setattr(pdf, "MAX_PAGES", 2)
    with pytest.raises(IngestError, match="more than 2 pages"):
        pdf.extract_pages(path)


def test_encrypted_pdf(tmp_path):
    path = tmp_path / "locked.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("secret-for-test")
    with path.open("wb") as handle:
        writer.write(handle)
    with pytest.raises(IngestError, match="encrypted"):
        pdf.extract_pages(path)
