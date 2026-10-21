"""Check and load the fixture corpus (Phase 0 exit criterion: "fixture corpus loads").

"Load" here means: register the ontology, the corpus, and one `documents` row per file
in Postgres, with its content hash, license, and trust level. Parsing and chunking
into text units come in Phase 1.

Usage, from the api/ folder:
    uv run python -m app.fixtures --check   # verify files and hashes only
    uv run python -m app.fixtures --load    # verify, then write to Postgres
"""

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, create_engine, text

from app.config import get_settings
from app.ontology import load_ontology

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_DIR = REPO_ROOT / "data" / "fixtures" / "research_v0"
DEFAULT_ONTOLOGY = REPO_ROOT / "ontology" / "research_v1.yaml"
CORPUS_NAME = "research_v0 (synthetic fixture)"
TRUST_LEVELS = {"high", "medium", "low"}


@dataclass(frozen=True)
class FixtureDoc:
    file: str
    title: str
    format: str
    license: str
    trust_level: str
    sha256: str
    source_uri: str


def read_manifest(fixture_dir: Path) -> list[FixtureDoc]:
    with (fixture_dir / "MANIFEST.csv").open(encoding="utf-8", newline="") as fh:
        return [FixtureDoc(**row) for row in csv.DictReader(fh)]


def check_fixtures(fixture_dir: Path) -> tuple[list[FixtureDoc], list[str]]:
    """Return (documents, problems). An empty problem list means every file is valid."""
    docs = read_manifest(fixture_dir)
    problems: list[str] = []
    for doc in docs:
        path = fixture_dir / doc.file
        if not path.is_file():
            problems.append(f"{doc.file}: file missing")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != doc.sha256:
            problems.append(f"{doc.file}: hash mismatch (file changed?)")
        if not doc.license.strip():
            problems.append(f"{doc.file}: license not recorded")
        if doc.trust_level not in TRUST_LEVELS:
            problems.append(f"{doc.file}: unknown trust level {doc.trust_level!r}")
    if len({d.sha256 for d in docs}) != len(docs):
        problems.append("duplicate documents (same content hash)")
    return docs, problems


def load_fixtures(engine: Engine, fixture_dir: Path, ontology_path: Path) -> int:
    """Write ontology, corpus and documents in one transaction. Safe to run again.

    Returns the number of documents the corpus has after loading.
    """
    docs, problems = check_fixtures(fixture_dir)
    if problems:
        raise ValueError("fixture check failed: " + "; ".join(problems))
    ontology = load_ontology(ontology_path)

    with engine.begin() as conn:  # one transaction: all rows or none
        ontology_id = conn.execute(
            text(
                "INSERT INTO ontologies (name, version, yaml) VALUES (:n, :v, :y) "
                "ON CONFLICT (name, version) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING id"
            ),
            {"n": ontology.name, "v": ontology.version, "y": ontology_path.read_text("utf-8")},
        ).scalar_one()

        corpus_id = conn.execute(
            text("SELECT id FROM corpora WHERE name = :n"), {"n": CORPUS_NAME}
        ).scalar()
        if corpus_id is None:
            corpus_id = conn.execute(
                text(
                    "INSERT INTO corpora (name, description, ontology_id) "
                    "VALUES (:n, :d, :o) RETURNING id"
                ),
                {"n": CORPUS_NAME, "d": "Ten synthetic papers for tests", "o": ontology_id},
            ).scalar_one()

        for doc in docs:
            conn.execute(
                text(
                    "INSERT INTO documents (corpus_id, title, source_uri, content_hash, "
                    "license, trust_level, metadata, status) "
                    "VALUES (:c, :t, :u, :h, :l, :tl, CAST(:m AS jsonb), 'registered') "
                    "ON CONFLICT (corpus_id, content_hash) DO NOTHING"
                ),
                {
                    "c": corpus_id,
                    "t": doc.title,
                    "u": doc.source_uri,
                    "h": doc.sha256,
                    "l": doc.license,
                    "tl": doc.trust_level,
                    "m": json.dumps({"file": doc.file, "format": doc.format}),
                },
            )

        return conn.execute(
            text("SELECT count(*) FROM documents WHERE corpus_id = :c"), {"c": corpus_id}
        ).scalar_one()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="verify files and hashes")
    group.add_argument("--load", action="store_true", help="verify, then write to Postgres")
    args = parser.parse_args(argv)

    docs, problems = check_fixtures(DEFAULT_FIXTURE_DIR)
    for problem in problems:
        print(f"PROBLEM: {problem}")
    print(f"{len(docs) - len(problems)} of {len(docs)} documents valid")
    if problems:
        return 1
    if args.load:
        engine = create_engine(get_settings().database_url.get_secret_value())
        try:
            count = load_fixtures(engine, DEFAULT_FIXTURE_DIR, DEFAULT_ONTOLOGY)
        finally:
            engine.dispose()
        print(f"Loaded: corpus '{CORPUS_NAME}' now has {count} documents")
    return 0


if __name__ == "__main__":
    sys.exit(main())
