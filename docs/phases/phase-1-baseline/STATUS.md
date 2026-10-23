# Phase 1 status

Last updated: 2026-10-23

## State

**In progress. Docker blocker resolved on 2026-10-23.** The stack runs on the owner's
Windows machine. No pipeline code written yet beyond the corpus scripts.

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

1. Owner fixes virtualization and WSL, then starts Docker Desktop (see owner steps in chat).
2. Claude runs `docker compose up -d --build`, checks `/api/v1/health` shows all `ok`.
3. Then: ingest (parse, hash, dedup, Postgres), chunking, embeddings, baseline answer,
   flow, evaluation set v0, results table.

## Local state

Branch `phase-1/baseline` has local commits only; nothing from Phase 1 is pushed yet.
`.env` is local and git-ignored.
