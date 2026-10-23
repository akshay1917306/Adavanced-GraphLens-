# Phase 1 status

Last updated: 2026-10-23

## State

**In progress. Ingest and chunking built and verified (steps 1 to 3 of 8).** Embeddings,
baseline answers, the flow and the evaluation set are not started.

## Completed

- Phase 0 approved, merged to `main` (commit 2f4a51c), tagged `phase-0`. CI was green.
- D3 closed: QA papers from the ACL Anthology (ACL and EMNLP 2022 and 2023).
- Corpus manifest and download scripts: 25 papers downloaded (26.8 MB), all recorded as
  CC BY 4.0 on the basis of the Anthology policy page; hashes stored; re-run skips all.
- Owner's `.env` set: OpenAI key present, Postgres and Neo4j passwords changed, models
  `LLM_MODEL_SMALL` and `LLM_MODEL_MAIN` both `gpt-4.1-mini`.
- Live check (2026-10-23): one call to `gpt-4.1-mini` returned `ok` (15 tokens, about
  $0.00001). Key and model work.
- CR-0001 (simplified dashboard, small evidence graph kept) drafted, not yet approved as a CR.

## Verified on the owner's machine (2026-10-23, run by Claude)

- Owner enabled CPU virtualization and installed WSL; Docker engine 29.9.2 runs.
- `docker compose up -d --build`: 5 containers up and healthy (Postgres, Neo4j, Qdrant,
  Redis, API). `GET /api/v1/health` returned `ok` for all four services.
- Alembic revision `0001` applied; 24 tables exist (23 blueprint tables plus `alembic_version`).
- Fixture load: 10 documents (9 medium, 1 low trust).
- Note: the fixture loader needs `data/` and `ontology/` mounted into the container
  (the image does not contain them):
  `docker compose run --rm --no-deps -v "$PWD/data:/data:ro" -v "$PWD/ontology:/ontology:ro" api python -m app.fixtures --load`

## Done after the Docker fix (2026-10-23, run by Claude on the owner's machine)

- PDF library chosen by measurement: pypdf (D15). `fonttools` added so pypdf decodes math fonts.
- New `pipeline/` package (Docker image, pinned deps in `uv.lock`): PDF reading with safety
  checks, cleaning (ligatures, hyphens, page numbers, headers, References cut, Acknowledgements
  dropped, NUL removed), section detection, sentence-aware chunking, ingest into Postgres.
- Real run: 25 of 25 papers ingested, 598 text units (17 to 600 tokens, average 371).
  Second run added nothing (25 skipped).
- Tests: 39 pass in Docker (unit and integration; integration tests create and drop their own
  throwaway database). `ruff check` and `ruff format --check` clean.
- Found and fixed while testing: a PDF with NUL characters crashed the insert; false headings
  (list items, algorithm lines, wrapped headings) created tiny chunks.

## Known limits of the cleaning (not fixed, recorded honestly)

- Footnote text can land in the middle of a sentence (for example a "Data and code available at
  ..." footnote). Layout hyphen and real hyphen are indistinguishable (`multi-hop` can become
  `multihop`).
- Everything after the References heading is dropped, including appendices.
- 14 chunks are under 50 tokens (short section introductions). Acceptable for the baseline.
- Equations, tables and figures come through as plain text and may be messy.
- If the chunker changes, the corpus must be re-ingested (rows are skipped by content hash);
  the manual re-ingest I did deleted only the `qa_v0` rows. A `--replace` option is a later idea.

## Current work

Nothing running.

## Blockers

1. The first image download was very slow (about 0.3 to 1 MB/s). Later builds use the cache.
2. Dev tools (uv, Node, pytest, ruff, Python 3.11) are not installed on Windows. Pipeline
   code and tests will run inside Docker instead. Ubuntu on WSL is optional.

## Decisions waiting for the owner

- Approve CR-0001 (simplified dashboard).
- Confirm models for later: both lines are `gpt-4.1-mini` for now. Revisit before Phase 2
  with an extraction cost estimate (ADR-0001 addendum to record final IDs and date).

## Exact next action

1. Embeddings: local `bge-base-en-v1.5` (about 440 MB download; check licence and
   compatibility first), dense plus sparse vectors into Qdrant, re-runnable.
2. Baseline answer: hybrid retrieval, bounded context, cited answer with the OpenAI model.
3. Prefect flow with checkpoints, then evaluation set v0 (30 local and 10 global questions,
   reviewed by the owner), and the baseline results table with cost.

Commands (from the repository folder, no Ubuntu needed):

    docker compose up -d                       # databases and API
    docker compose run --rm pipeline ingest    # parse, chunk and store the 25 papers
    docker compose run --rm --entrypoint pytest pipeline -q   # tests

## Local state

Branch `phase-1/baseline` has local commits only; nothing from Phase 1 is pushed yet.
`.env` is local and git-ignored.
