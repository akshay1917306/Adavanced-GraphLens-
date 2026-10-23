"""Read the text of a PDF with pypdf, after basic safety checks.

Why pypdf: it kept normal word spacing and read two-column papers in order in our test
(docs/DECISIONS.md, D15). Its output still needs cleaning (see cleaning.py).
"""

from pathlib import Path

from pypdf import PdfReader

from graphlens_pipeline.errors import IngestError

MAX_PDF_BYTES = 20 * 1024 * 1024  # a research paper is a few MB; refuse anything huge
MAX_PAGES = 60
MIN_TEXT_CHARS = 500  # less than this usually means a scanned or empty PDF


def extract_pages(path: Path) -> list[str]:
    """Return the text of each page. Raises IngestError for anything unsafe or unreadable."""
    if not path.is_file():
        raise IngestError("file is missing")
    size = path.stat().st_size
    if size == 0:
        raise IngestError("file is empty")
    if size > MAX_PDF_BYTES:
        raise IngestError(f"file is larger than {MAX_PDF_BYTES // (1024 * 1024)} MB")
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise IngestError("file is not a PDF")

    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise IngestError("PDF is encrypted")
        if len(reader.pages) > MAX_PAGES:
            raise IngestError(f"PDF has more than {MAX_PAGES} pages")
        pages = [page.extract_text() or "" for page in reader.pages]
    except IngestError:
        raise
    except Exception as error:  # pypdf raises many types for broken files
        raise IngestError(f"PDF could not be read ({type(error).__name__})") from error

    if sum(len(page) for page in pages) < MIN_TEXT_CHARS:
        raise IngestError("PDF has no extractable text (scanned?)")
    return pages
