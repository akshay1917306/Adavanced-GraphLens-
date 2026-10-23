"""Ingest a corpus manifest into Postgres: documents and their text units.

Safe to run again: a document with the same content hash in the same corpus is skipped.
Each document is written in one transaction, so a failure never leaves half a document.

Section names are not a column of `text_units` in the blueprint schema, so they are stored
in `documents.metadata` as `unit_sections` (a list indexed by unit ordinal). See D16.
"""

import csv
import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import tiktoken
from sqlalchemy import Engine, text

from graphlens_pipeline.chunking import (
    CHUNKER_VERSION,
    ENCODING_NAME,
    OVERLAP_TOKENS,
    TARGET_TOKENS,
    chunk_sections,
    get_encoding,
)
from graphlens_pipeline.cleaning import clean_pages
from graphlens_pipeline.errors import IngestError
from graphlens_pipeline.pdf import extract_pages

# Decision D3: only papers under a plain CC BY license enter the corpus.
ALLOWED_LICENSE = re.compile(r"CC BY( \d\.\d)?")
TRUST_LEVEL = "medium"


@dataclass
class IngestReport:
    ingested: int = 0
    skipped_duplicates: int = 0
    text_units: int = 0
    failures: dict[str, str] = field(default_factory=dict)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def unit_id(content_hash: str, ordinal: int) -> str:
    """Stable ID for a text unit: the same file and chunker always give the same IDs."""
    return f"u_{content_hash[:12]}_{ordinal:04d}"


def _ensure_corpus(engine: Engine, name: str, description: str) -> str:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM corpora WHERE name = :name"), {"name": name}
        ).first()
        if row:
            return str(row[0])
        created = conn.execute(
            text("INSERT INTO corpora (name, description) VALUES (:name, :desc) RETURNING id"),
            {"name": name, "desc": description},
        ).one()
        return str(created[0])


def _check_license(license_name: str) -> None:
    if not ALLOWED_LICENSE.fullmatch(license_name.strip()):
        raise IngestError("license is missing or is not plain CC BY")


def _ingest_one(
    engine: Engine,
    corpus_id: str,
    row: dict[str, str],
    pdf_dir: Path,
    extract: Callable[[Path], list[str]],
    enc: tiktoken.Encoding,
) -> tuple[bool, int]:
    """Ingest one manifest row. Returns (was_new, number_of_text_units)."""
    _check_license(row.get("license", ""))
    path = pdf_dir / f"{row['paper_id']}.pdf"
    if not path.is_file():
        raise IngestError("file is missing")
    content_hash = sha256_file(path)
    expected = row.get("sha256", "").strip()
    if expected and expected != content_hash:
        raise IngestError("file changed since it was downloaded (hash mismatch)")

    pages = extract(path)
    sections = clean_pages(pages)
    chunks = chunk_sections(sections, enc)
    if not chunks:
        raise IngestError("no text left after cleaning")

    metadata = {
        "paper_id": row["paper_id"],
        "year": row.get("year"),
        "venue": row.get("venue"),
        "authors": row.get("authors"),
        "license_basis_url": row.get("license_basis_url"),
        "pdf_pages": len(pages),
        "chunker": {
            "version": CHUNKER_VERSION,
            "target_tokens": TARGET_TOKENS,
            "overlap_tokens": OVERLAP_TOKENS,
            "encoding": ENCODING_NAME,
        },
        "unit_sections": [chunk.section for chunk in chunks],
    }
    with engine.begin() as conn:  # one transaction: the document and all its units, or nothing
        inserted = conn.execute(
            text(
                "INSERT INTO documents (corpus_id, title, source_uri, content_hash, license,"
                " trust_level, metadata)"
                " VALUES (:corpus_id, :title, :source_uri, :content_hash, :license,"
                " :trust, CAST(:metadata AS jsonb))"
                " ON CONFLICT (corpus_id, content_hash) DO NOTHING RETURNING id"
            ),
            {
                "corpus_id": corpus_id,
                "title": row["title"],
                "source_uri": row["pdf_url"],
                "content_hash": content_hash,
                "license": row["license"].strip(),
                "trust": TRUST_LEVEL,
                "metadata": json.dumps(metadata),
            },
        ).first()
        if inserted is None:
            return False, 0
        conn.execute(
            text(
                "INSERT INTO text_units (id, document_id, ordinal, text, token_count, content_hash)"
                " VALUES (:id, :document_id, :ordinal, :text, :token_count, :content_hash)"
            ),
            [
                {
                    "id": unit_id(content_hash, chunk.ordinal),
                    "document_id": str(inserted[0]),
                    "ordinal": chunk.ordinal,
                    "text": chunk.text,
                    "token_count": chunk.token_count,
                    "content_hash": hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                }
                for chunk in chunks
            ],
        )
    return True, len(chunks)


def ingest_manifest(
    engine: Engine,
    manifest: Path,
    pdf_dir: Path,
    corpus_name: str,
    corpus_description: str,
    extract: Callable[[Path], list[str]] = extract_pages,
) -> IngestReport:
    """Ingest every paper in the manifest. One bad paper is reported and the rest continue."""
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    corpus_id = _ensure_corpus(engine, corpus_name, corpus_description)
    enc = get_encoding()
    report = IngestReport()
    for row in rows:
        paper_id = row.get("paper_id", "?")
        try:
            was_new, units = _ingest_one(engine, corpus_id, row, pdf_dir, extract, enc)
        except IngestError as error:
            report.failures[paper_id] = str(error)
            continue
        except Exception as error:  # unexpected: report the type only, never raw details
            report.failures[paper_id] = f"unexpected error ({type(error).__name__})"
            continue
        if was_new:
            report.ingested += 1
            report.text_units += units
        else:
            report.skipped_duplicates += 1
    return report
