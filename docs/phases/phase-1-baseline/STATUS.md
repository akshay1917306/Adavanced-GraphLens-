# Phase 1 status

Last updated: 2026-10-23

## State

**In progress, blocked on the owner's machine (Docker cannot start).** No pipeline code
written yet beyond the corpus scripts.

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

## Current work

Nothing running.

## Blockers

1. **Docker engine does not start on the owner's Windows machine.** Findings:
   `docker info` says "Docker Desktop is unable to start"; the Docker log says the engine
   has not answered for 11+ hours; `wsl --status` prints only its help text (WSL not set
   up); firmware virtualization reports `False`. Fix needs the owner: enable CPU
   virtualization in BIOS, run `wsl --install` as administrator, restart.
2. Dev tools missing on Windows (uv, Node, pytest, ruff, Python 3.11). The repo is designed
   for Ubuntu on WSL; installing it in WSL solves this too.

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
