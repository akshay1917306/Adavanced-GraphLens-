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

## Step 4: the paid 5% sample (2026-10-24, Claude, owner approved about $0.11)

Fixed sample of **43 units** (`gpt-4.1-mini`, prompt `extract-v1`). Money spent in Phase 2 so far:
about **$0.12** (g0 $0.045, g2 $0.067, one failed unit finished $0.004, one diagnosis call $0.002).

| | Gleaning 0 | Gleaning 2 |
|---|---|---|
| Cost for the 43 units | $0.045 ($0.00105 per unit) | $0.071 ($0.0017 per unit) |
| Entities on the same 42 units | 210 | 227 (+8%) |
| Relations on the same 42 units | 139 | 169 (+22%) |
| Units where gleaning added something | | 18 of 42 |
| Average gleaning passes actually done | | 1.07 of 2 (stops early) |

- **Projected full run (751 units) at the measured rates:** about **$0.79** (gleaning 0) or about
  **$1.30** (gleaning 2). The free estimate said $0.64 and $1.57; answers were longer than assumed.
- **Quality is not measured yet.** Gleaning adds items, but we do not know if the added ones are
  right; that needs the labeled units (precision 0.80 target). My informal read of 4 sampled units:
  the abstract unit was good; a short unit correctly gave nothing; the SQUIRE introduction gave
  correct entities but only 1 of 5 attempted relations survived.
- **About 24% of attempted relations are dropped** (`relation_end_not_in_entities` 24 and
  `type_not_allowed_for_predicate` 25 in the g0 run, against 157 kept). The second reason is the
  ontology: `USES` goes only from Paper to Method or Dataset, so true statements such as "SQUIRE
  uses a Transformer" (Method to Method) or "method uses dataset" are dropped. Blueprint decision
  D4 says to start small and widen when the audit shows gaps. Proposal for the owner: widen
  `USES` to start at Paper or Method (new ontology version 2, which also changes cache keys).
- One unit (a table of numbers) failed in the gleaning run: the answer was cut off at the old
  1,500-token output limit. The limit is now 3,000, a cut-off answer is reported as such, and the
  unit was finished in the second run.
- Other things seen: a vague phrase such as "three MHQA datasets" is stored as a Dataset (noise to
  watch in the audit); one `CITES` edge appeared although references are cut.
- Test environment: the Prefect temporary server needs 30 to 40 s on this machine (free RAM about
  3 GB); the tests wait up to 120 s now (`PREFECT_SERVER_EPHEMERAL_STARTUP_TIMEOUT_SECONDS` and
  `server_startup_timeout`). 153 tests pass. `ruff` clean.

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

The owner decides two things (asked in chat):
1. Widen `USES` (ontology version 2: Paper or Method to Method or Dataset)? If yes, Claude edits
   `ontology/research_v1.yaml` into a v2 file, records the decision, and the sample is re-run
   with the new ontology (cache keys change; about $0.12 more).
2. Full extraction on all 751 units, which gleaning setting, and the cost cap. Suggested: run
   gleaning 0 and gleaning 2 both (about $0.8 and $1.3, cap $3 in total), so the labeled units can
   decide D6 by measured precision instead of a guess.

Then build steps 6 to 10 in BRIEF.md: entity resolution, Neo4j load, quality report, labeled
sets, tests and docs. Command for the full run:
`docker compose run --rm pipeline extract --sample 1 --gleaning 0 --max-cost-usd 1.5 --index-version idx-1-g0`.

## Notes for the next session

- Run everything through Docker; repository folder:
  `C:\Users\ACER\Downloads\Advanced GraphLens\Adavanced-GraphLens-`.
- `docker compose up -d --wait` starts the stack; `docker compose run --rm pipeline ...` runs
  the commands. Qdrant also holds unrelated sample collections (`dinosaurs` and others); they are
  not ours.
