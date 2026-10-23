"""The indexing flow: ingest the papers, then embed them (blueprint 2.5, stages 1 to 6 so far).

Each stage is a Prefect task with a few retries for transient trouble (a dropped connection).
Resuming a failed run does not repeat finished work because the stages themselves are
idempotent: ingest skips documents it already has (same content hash) and embed skips units
that already have a point in Qdrant. So a retry or a second run continues where the first
stopped. Prefect's own run records are temporary (they live in the container), so the
database, not Prefect, is the source of truth.

A paper that cannot be ingested (bad license, broken PDF) is a data problem, not a transient
one. It is reported in the summary and is not retried.

Not here yet: the `index_runs` and `run_stages` tables. They describe versioned index runs,
which start in Phase 2 together with the quality gate.
"""

from pathlib import Path

from prefect import flow, get_run_logger, task
from prefect.cache_policies import NO_CACHE
from qdrant_client import QdrantClient
from sqlalchemy import create_engine

from graphlens_pipeline.embed import FastEmbedder, embed_corpus
from graphlens_pipeline.ingest import ingest_manifest

# Replaced by a mock in tests; the real command uses the local models.
EMBEDDER_FACTORY = FastEmbedder

RETRIES = 2
RETRY_DELAY_SECONDS = 5


@task(
    name="ingest", retries=RETRIES, retry_delay_seconds=RETRY_DELAY_SECONDS, cache_policy=NO_CACHE
)
def ingest_stage(
    database_url: str, manifest: str, pdf_dir: str, corpus_name: str, corpus_description: str
) -> dict:
    log = get_run_logger()
    engine = create_engine(database_url)
    report = ingest_manifest(engine, Path(manifest), Path(pdf_dir), corpus_name, corpus_description)
    log.info(
        "ingest: %d new, %d already present, %d text units, %d failed",
        report.ingested, report.skipped_duplicates, report.text_units, len(report.failures),
    )  # fmt: skip
    return {
        "ingested": report.ingested,
        "skipped": report.skipped_duplicates,
        "text_units": report.text_units,
        "failures": report.failures,
    }


@task(name="embed", retries=RETRIES, retry_delay_seconds=RETRY_DELAY_SECONDS, cache_policy=NO_CACHE)
def embed_stage(
    database_url: str,
    qdrant_url: str,
    corpus_name: str,
    corpus_slug: str,
    index_version: str,
    make_live: bool,
    batch_size: int,
) -> dict:
    log = get_run_logger()
    report = embed_corpus(
        create_engine(database_url),
        QdrantClient(url=qdrant_url),
        corpus_name,
        corpus_slug,
        index_version,
        EMBEDDER_FACTORY(),
        batch_size=batch_size,
        make_live=make_live,
    )
    log.info(
        "embed: %d new, %d already present, %d too long for the model",
        report.embedded, report.skipped, report.truncated,
    )  # fmt: skip
    return {
        "collection": report.collection,
        "embedded": report.embedded,
        "skipped": report.skipped,
        "truncated": report.truncated,
    }


@flow(name="index-baseline", log_prints=False)
def index_baseline(
    database_url: str,
    qdrant_url: str,
    manifest: str,
    pdf_dir: str,
    corpus_name: str,
    corpus_description: str,
    corpus_slug: str,
    index_version: str,
    make_live: bool = True,
    batch_size: int = 32,
) -> dict:
    """Ingest then embed. Returns a summary; `failures` lists papers that were not ingested."""
    ingest = ingest_stage(database_url, manifest, pdf_dir, corpus_name, corpus_description)
    embed = embed_stage(
        database_url, qdrant_url, corpus_name, corpus_slug, index_version, make_live, batch_size
    )
    return {"ingest": ingest, "embed": embed}
