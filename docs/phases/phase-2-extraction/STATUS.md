# Phase 2 status

Last updated: 2026-10-24

## State

**Started. Planning docs written; step 1 (front-matter unit, CR-0003) is half done.** Nothing
from Phase 2 is pushed. Local branch `phase-2/extraction`, branched from `main` at 72542d6
(which is tagged `phase-1`).

## Completed

- Owner approved the Phase 2 plan and chose option A (keep a front-matter unit) on 2026-10-24.
- BRIEF, PREREQUISITES, CHECKLIST, PROMPT, and CR-0003 written (committed).

## Current work (uncommitted, untested)

Edited but **not yet formatted, linted or tested**, because Docker's engine would not start:

- `pipeline/graphlens_pipeline/cleaning.py`: keeps the `Front matter` section and removes lines
  with an email or web address from it (`CONTACT_LINE`).
- `pipeline/graphlens_pipeline/chunking.py`: `CHUNKER_VERSION = "3"`.
- `pipeline/tests/test_cleaning.py`: first test updated, two tests added.

## Blockers

1. **Docker engine is stopped** on the owner's machine (Docker Desktop app is open, its WSL
   `docker-desktop` distro says Stopped). The owner must open Docker Desktop and wait until the
   engine is running (green). Claude cannot click inside Docker Desktop.

## Exact next action

1. When Docker runs: `docker compose up -d --wait`, then format, lint and test the three
   edits above (`ruff format`, `ruff check`, `pytest`), and fix what fails.
2. Re-ingest the development corpus from scratch (replace only the `qa_v0` rows), embed into
   `units_qa_v0_baseline_2`, move the `units_live` alias, delete the old collection
   `units_qa_v0_baseline_1`.
3. Remap the evaluation evidence by exact quote (each quote must be found in exactly one unit of
   the same paper), save it, load it as evaluation set version 2 (`eval-load --version 2` needs
   to be added), keep version 1 and the Phase 1 results.
4. Commit step 1, then continue with build step 2 in BRIEF.md (ontology schema and prompt).

## Notes for the next session

- Run everything through Docker; the repository folder is
  `C:\Users\ACER\Downloads\Advanced GraphLens\Adavanced-GraphLens-`.
- The Phase 1 baseline results stay as recorded; they are not re-run (it costs money).
