"""Shared test helpers: fake papers, a tiny real PDF builder, and a throwaway database."""

import os
import textwrap
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url


def sentences(count: int, topic: str = "question answering") -> str:
    return " ".join(
        f"Sentence {i} explains how {topic} systems retrieve evidence from documents."
        for i in range(count)
    )


def fake_pages(seed: str = "a", body_sentences: int = 40) -> list[str]:
    """Pages that look like a two-section paper: header, abstract, introduction, references."""
    abstract = textwrap.fill(sentences(8, f"{seed} abstract"), 70)
    intro = textwrap.fill(sentences(body_sentences, f"{seed} intro"), 70)
    method = textwrap.fill(sentences(body_sentences, f"{seed} method"), 70)
    refs = "Smith, J. 2020. A reference entry that must be dropped."
    return [
        "Proceedings of the 60th Annual Meeting\nA Paper About Things\nJane Author\n"
        f"Abstract\n{abstract}\n1",
        f"1 Introduction\n{intro}\n2",
        f"2 Method\n{method}\n3",
        f"References\n{refs}\n4",
    ]


def make_text_pdf(path: Path, lines: list[str]) -> None:
    """Write a minimal valid one-page PDF whose page text is `lines` (plain ASCII only)."""
    content = (
        "BT /F1 10 Tf 12 TL 40 760 Td\n"
        + "\n".join(
            f"({line.replace('(', '').replace(')', '').replace(chr(92), '')}) Tj T*"
            for line in lines
        )
        + "\nET"
    )
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        " /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    out += trailer.encode()
    path.write_bytes(bytes(out))


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    """A brand-new database that exists only for this test run. It never touches real data."""
    url = os.environ.get("DATABASE_URL")
    schema = os.environ.get("SCHEMA_SQL")
    if not url or not schema or not Path(schema).is_file():
        pytest.skip("needs DATABASE_URL and SCHEMA_SQL (run through docker compose)")
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    name = f"pipeline_test_{uuid.uuid4().hex[:8]}"
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    test_engine = create_engine(make_url(url).set(database=name))
    raw = test_engine.raw_connection()
    try:
        raw.cursor().execute(Path(schema).read_text(encoding="utf-8"))
        raw.commit()
    finally:
        raw.close()
    try:
        yield test_engine
    finally:
        test_engine.dispose()
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()
