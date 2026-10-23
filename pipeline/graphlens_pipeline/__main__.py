"""Command line for the pipeline.

docker compose run --rm pipeline ingest
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine

from graphlens_pipeline.embed import MAX_INPUT_TOKENS
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
    embed = sub.add_parser("embed", help="embed text units into Qdrant (local models, no cost)")
    embed.add_argument("--corpus-name", default=DEFAULT_CORPUS)
    embed.add_argument("--corpus-slug", default="qa_v0")
    embed.add_argument("--index-version", default="baseline-1")
    embed.add_argument("--batch-size", type=int, default=32)
    embed.add_argument("--no-live", action="store_true", help="do not move the units_live alias")
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 2
    engine = create_engine(database_url)  # the URL is never printed

    if args.command == "embed":
        qdrant_url = os.environ.get("QDRANT_URL")
        if not qdrant_url:
            print("QDRANT_URL is not set.", file=sys.stderr)
            return 2
        from qdrant_client import QdrantClient

        from graphlens_pipeline.embed import FastEmbedder, embed_corpus

        result = embed_corpus(
            engine,
            QdrantClient(url=qdrant_url),
            args.corpus_name,
            args.corpus_slug,
            args.index_version,
            FastEmbedder(),
            batch_size=args.batch_size,
            make_live=not args.no_live,
        )
        print(
            f"Collection {result.collection}: embedded {result.embedded}, "
            f"skipped {result.skipped} already present, "
            f"{result.truncated} units longer than {MAX_INPUT_TOKENS} model tokens (tail cut)."
        )
        return 0

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
