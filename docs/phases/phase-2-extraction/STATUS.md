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

## Steps 2 and 3 (2026-10-24, Claude, nothing paid yet)

- `ontology.py`: ontology checks, a fingerprint for cache keys, and the strict JSON schema for the
  model's answer. `extract.py`: the prompt (untrusted-text rule, paper title and section given),
  a second answer check, up to 3 attempts, gleaning passes (relations may end at entities found
  earlier), cache, cost cap, 4 parallel workers. `runs.py`: `index_runs` and `run_stages` rows.
- New commands: `extract-estimate` (free), `extract` (paid; `--sample`, `--gleaning`,
  `--max-cost-usd`, `--index-version`).
- A test found a real bug before any money was spent: a gleaning relation that ended at an entity
  from an earlier pass was dropped. Fixed and tested.
- Tests: 152 pass in Docker (model mocked and labelled). `ruff` clean.
- **Free cost estimate on the real 751 units** (`gpt-4.1-mini`; prompt tokens counted exactly,
  answer sizes assumed: 350 tokens first pass, 120 per gleaning pass):
  gleaning 0: about **$0.64**; gleaning 2: up to about **$1.57** (upper bound, since a pass that
  finds nothing new stops early). The 5% sample (about 38 units) would cost about $0.03 and $0.08.
- Cost cap: new units stop being started once the spent amount reaches the cap; units already
  running finish, so the cap can be passed by up to `workers` units' cost.

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

Build step 4: the paid 5% sample runs. **The owner must say yes first.** Plan: two runs on the
same fixed 5% sample (about 38 units), gleaning 0 then gleaning 2, each with
`--max-cost-usd 0.25`, expected total about $0.11 (estimate). Then Claude reads the sample output
against the source text, reports what was missed and what was wrong (a first, informal quality
look), and compares gleaning 0 and 2 (D6) and the model (D5). After that, the owner decides the
full run (about $0.64 or $1.57, estimates). Commands:
`docker compose run --rm pipeline extract --sample 0.05 --gleaning 0 --index-version idx-sample-g0`
and the same with `--gleaning 2 --index-version idx-sample-g2`.

## Notes for the next session

- Run everything through Docker; repository folder:
  `C:\Users\ACER\Downloads\Advanced GraphLens\Adavanced-GraphLens-`.
- `docker compose up -d --wait` starts the stack; `docker compose run --rm pipeline ...` runs
  the commands. Qdrant also holds unrelated sample collections (`dinosaurs` and others); they are
  not ours.
