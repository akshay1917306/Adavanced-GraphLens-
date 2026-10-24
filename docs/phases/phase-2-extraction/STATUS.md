# Phase 2 status

Last updated: 2026-10-24

## State

**In progress. Build step 1 of 10 (CR-0003, front-matter unit) is done and verified.** Nothing
from Phase 2 is pushed. Local branch `phase-2/extraction`, branched from `main` at 72542d6
(tagged `phase-1`).

## Completed

- Owner approved the Phase 2 plan and chose option A (keep a front-matter unit), 2026-10-24.
- BRIEF, PREREQUISITES, CHECKLIST, PROMPT and CR-0003 written.
- Step 1: `Front matter` kept as the first unit of each paper (emails and web lines removed),
  chunker version 3. The `qa_v0` corpus was re-ingested: 25 papers, **751 text units** (17 to 450
  tokens, average 300), 25 of them front matter. Re-embedded into `units_qa_v0_baseline_2`
  (751 points); alias `units_live` points to it; the old collection `baseline_1` was deleted.
- Evaluation evidence remapped by exact quote (when neighbouring units overlap, the first unit is
  used) and loaded as evaluation sets version 2 (30 local, 10 global). Version 1 and the Phase 1
  results (40 rows) are untouched. `eval-verify`: 40 questions, 25 evidence units, 0 problems.
- Tests: 111 pass in Docker. `ruff` clean. One live question after the change: answered with valid
  citations, cost $0.00101.
- The Phase 1 baseline numbers were measured on the old units and were not re-run (it costs money).

## Things that went wrong and were fixed (so the next session knows)

- Docker's engine was stopped after a reboot. Quitting Docker Desktop, running `wsl --shutdown`
  and starting Docker Desktop again fixed it.
- I loaded evaluation set version 2 once before the remap had succeeded, so it held old unit
  IDs. I noticed, deleted only version 2 (no results pointed to it) and loaded it again after
  the remap and a passing `eval-verify`.

## Blockers

None.

## Decisions waiting for the owner

- OpenAI monthly limit of about $5 or more in the OpenAI dashboard (PREREQUISITES item 3).

## Exact next action

Build step 2: ontology to a strict JSON schema, extraction prompt v1, extraction cache (see
BRIEF.md). Then step 3 (run records and cost cap) and step 4 (the 5% dry run with a cost estimate
to show the owner before any paid batch).

## Notes for the next session

- Run everything through Docker; repository folder:
  `C:\Users\ACER\Downloads\Advanced GraphLens\Adavanced-GraphLens-`.
- `docker compose up -d --wait` starts the stack; `docker compose run --rm pipeline ...` runs
  the commands. Qdrant also holds unrelated sample collections (`dinosaurs` and others); they are
  not ours.
