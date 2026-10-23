"""Command line for the pipeline.

docker compose run --rm pipeline ingest
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine

from graphlens_pipeline.ingest import ingest_manifest

DEFAULT_CORPUS = "qa_v0 (ACL Anthology QA papers)"
DEFAULT_DESCRIPTION = "Question answering papers, ACL and EMNLP 2022-2023, CC BY 4.0"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="graphlens_pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="parse, chunk and store the papers of a manifest")
    ingest.add_argument("--manifest", type=Path, default=Path("/data/corpus/qa_v0/manifest.csv"))
    ingest.add_argument("--pdf-dir", type=Path, default=Path("/data/corpus/qa_v0/pdfs"))
    ingest.add_argument("--corpus-name", default=DEFAULT_CORPUS)
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 2
    engine = create_engine(database_url)  # the URL is never printed

    report = ingest_manifest(
        engine, args.manifest, args.pdf_dir, args.corpus_name, DEFAULT_DESCRIPTION
    )
    print(
        f"Ingested {report.ingested} new documents ({report.text_units} text units); "
        f"skipped {report.skipped_duplicates} already present."
    )
    for paper_id, reason in report.failures.items():
        print(f"FAILED {paper_id}: {reason}", file=sys.stderr)
    return 1 if report.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
