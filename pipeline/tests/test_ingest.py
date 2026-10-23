"""Integration tests: need the Postgres container. They use their own throwaway database."""

import csv
import hashlib
from pathlib import Path

import pytest
from sqlalchemy import text

from graphlens_pipeline.ingest import ingest_manifest, unit_id
from tests.conftest import fake_pages

pytestmark = pytest.mark.integration

FIELDS = [
    "paper_id",
    "title",
    "year",
    "venue",
    "authors",
    "pdf_url",
    "page_url",
    "license",
    "license_basis_url",
    "retrieved_on",
    "sha256",
    "bytes",
]


def write_corpus(root: Path, papers: dict[str, dict]) -> tuple[Path, Path]:
    """Create dummy PDF files (their bytes only matter for hashing) and a manifest."""
    pdf_dir = root / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for paper_id, options in papers.items():
        content = options.get("content", f"dummy pdf for {paper_id}".encode())
        if options.get("write_file", True):
            (pdf_dir / f"{paper_id}.pdf").write_bytes(content)
        rows.append(
            {
                "paper_id": paper_id,
                "title": f"Title of {paper_id}",
                "year": "2023",
                "venue": "ACL",
                "authors": "A; B",
                "pdf_url": f"https://example.org/{paper_id}.pdf",
                "page_url": "",
                "license": options.get("license", "CC BY 4.0"),
                "license_basis_url": "https://aclanthology.org/faq/copyright/",
                "retrieved_on": "",
                "sha256": options.get("sha256", hashlib.sha256(content).hexdigest()),
                "bytes": str(len(content)),
            }
        )
    manifest = root / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return manifest, pdf_dir


def extractor(pages_by_paper: dict[str, list[str]]):
    def extract(path: Path) -> list[str]:
        result = pages_by_paper[path.stem]
        if isinstance(result, Exception):
            raise result
        return result

    return extract


def count(engine, table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def reset(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE text_units, documents, corpora CASCADE"))


def test_ingest_stores_documents_and_units(engine, tmp_path):
    reset(engine)
    manifest, pdf_dir = write_corpus(tmp_path, {"p1": {}, "p2": {}})
    extract = extractor({"p1": fake_pages("one"), "p2": fake_pages("two")})
    report = ingest_manifest(engine, manifest, pdf_dir, "test corpus", "d", extract)

    assert report.ingested == 2 and not report.failures
    assert count(engine, "documents") == 2
    assert count(engine, "text_units") == report.text_units > 2
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT d.content_hash, d.license, d.trust_level, d.metadata, u.id, u.ordinal,"
                " u.token_count FROM documents d JOIN text_units u ON u.document_id = d.id"
            )
        ).all()
    assert all(r.license == "CC BY 4.0" and r.trust_level == "medium" for r in rows)
    assert all(r.token_count <= 600 for r in rows)
    assert all(r.id == unit_id(r.content_hash, r.ordinal) for r in rows)
    by_doc: dict[str, list] = {}
    for r in rows:
        by_doc.setdefault(r.content_hash, []).append(r)
    for doc_rows in by_doc.values():
        ordinals = sorted(r.ordinal for r in doc_rows)
        assert ordinals == list(range(len(ordinals)))
        sections = doc_rows[0].metadata["unit_sections"]
        assert len(sections) == len(ordinals)
        assert "References" not in sections


def test_text_with_nul_characters_can_be_stored(engine, tmp_path):
    reset(engine)
    manifest, pdf_dir = write_corpus(tmp_path, {"p1": {}})
    pages = [page.replace("Sentence 3", "Sentence\x00 3") for page in fake_pages()]
    report = ingest_manifest(
        engine, manifest, pdf_dir, "test corpus", "d", extractor({"p1": pages})
    )
    assert report.ingested == 1 and not report.failures


def test_running_twice_adds_nothing(engine, tmp_path):
    reset(engine)
    manifest, pdf_dir = write_corpus(tmp_path, {"p1": {}, "p2": {}})
    extract = extractor({"p1": fake_pages("one"), "p2": fake_pages("two")})
    first = ingest_manifest(engine, manifest, pdf_dir, "test corpus", "d", extract)
    units_after_first = count(engine, "text_units")
    second = ingest_manifest(engine, manifest, pdf_dir, "test corpus", "d", extract)

    assert first.ingested == 2
    assert second.ingested == 0 and second.skipped_duplicates == 2 and not second.failures
    assert count(engine, "documents") == 2
    assert count(engine, "text_units") == units_after_first
    assert count(engine, "corpora") == 1


def test_same_file_under_another_name_is_a_duplicate(engine, tmp_path):
    reset(engine)
    same = b"identical bytes"
    manifest, pdf_dir = write_corpus(tmp_path, {"p1": {"content": same}, "p2": {"content": same}})
    extract = extractor({"p1": fake_pages("one"), "p2": fake_pages("one")})
    report = ingest_manifest(engine, manifest, pdf_dir, "test corpus", "d", extract)
    assert report.ingested == 1 and report.skipped_duplicates == 1
    assert count(engine, "documents") == 1


def test_license_other_than_plain_cc_by_is_rejected(engine, tmp_path):
    reset(engine)
    papers = {"nc": {"license": "CC BY-NC 4.0"}, "blank": {"license": ""}, "ok": {}}
    manifest, pdf_dir = write_corpus(tmp_path, papers)
    pages = {name: fake_pages(name) for name in papers}
    report = ingest_manifest(engine, manifest, pdf_dir, "test corpus", "d", extractor(pages))
    assert set(report.failures) == {"nc", "blank"}
    assert report.ingested == 1
    assert count(engine, "documents") == 1


def test_changed_file_is_rejected(engine, tmp_path):
    reset(engine)
    manifest, pdf_dir = write_corpus(tmp_path, {"p1": {"sha256": "0" * 64}})
    report = ingest_manifest(
        engine, manifest, pdf_dir, "test corpus", "d", extractor({"p1": fake_pages()})
    )
    assert "hash mismatch" in report.failures["p1"]
    assert count(engine, "documents") == 0


def test_a_bad_paper_does_not_stop_the_batch_and_leaves_no_rows(engine, tmp_path):
    reset(engine)
    papers = {"missing": {"write_file": False}, "boom": {}, "empty": {}, "good": {}}
    manifest, pdf_dir = write_corpus(tmp_path, papers)
    pages = {
        "boom": RuntimeError("secret-looking detail that must not be echoed"),
        "empty": [""],
        "good": fake_pages("good"),
        "missing": fake_pages("missing"),
    }
    report = ingest_manifest(engine, manifest, pdf_dir, "test corpus", "d", extractor(pages))

    assert report.ingested == 1
    assert set(report.failures) == {"missing", "boom", "empty"}
    assert "secret-looking" not in " ".join(report.failures.values())  # only the type is shown
    assert count(engine, "documents") == 1
    with engine.connect() as conn:
        assert conn.execute(text("SELECT title FROM documents")).scalar_one() == "Title of good"
