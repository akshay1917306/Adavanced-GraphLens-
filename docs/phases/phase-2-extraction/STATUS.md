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

## Ontology v2 and the full extraction (2026-10-24, owner approved up to $3)

- Ontology v2 (`ontology/research_v2.yaml`): only `USES` changed (Paper or Method to Method or
  Dataset), decision D24. v1 stays as history. The CLI default is v2.
- Sample under v2 (43 units): relations 157 -> 191 for gleaning 0 (+22%), type-mismatch rejections
  25 -> 12. Under v2 gleaning 2 gave 193 relations against 191, so gleaning barely helps there.
- **Full run, 751 units, `gpt-4.1-mini`, ontology v2** (raw, before entity resolution):

| | Gleaning 0 (`idx2-full-g0`) | Gleaning 2 (`idx2-full-g2`) |
|---|---|---|
| Entity mentions | 4,591 | 4,781 (+4%) |
| Relations kept | 3,611 | 3,763 (+4%) |
| Rejected by the ontology rules | 377 type mismatch, 196 loose ends | 495 and 135 |
| Cost | $0.766 | $1.249 (+63%) |
| Failed units | 0 (one network error, finished in a second call for $0.0006) | 0 |

- **Reading:** on the whole corpus gleaning adds about 4% more items for 63% more money. Whether
  the extra items are correct is **not measured**; that needs the labeled units. For now gleaning
  0 is the working choice (decision D6 stays open until precision is measured).
- Money spent in Phase 2 so far (from `index_runs`): **$2.24**.
- Run records: `idx2-full-g0` and `idx2-full-g2` stay `running` until the quality gate decides.

## Step 6: entity resolution (2026-10-24, Claude, built; precision NOT yet measured)

- Code: `pipeline/graphlens_pipeline/resolve.py`, CLI `resolve`, 46 tests in `tests/test_resolve.py`.
  Whole suite: 198 passed (1 model test deselected); ruff check and format clean.
- Result on the `idx2-full-g0` results (4,591 mentions): **1,848 entities**, 2,695 relations.
  Decisions stored in `resolution_decisions`: 80 auto merges, 52 model merges, 527 model "keep
  separate" (includes the merges the guard overruled), 62 rule-blocked. Judge calls run 8 at a
  time: 2 min 19 s instead of 25+ min. Judge answers are cached, so re-runs cost nothing.
- Rules alone give 1,884 entities.
- **Merge guard (`merge_veto`)**: the first model pass said "same" 164 times, and in the first
  100 I read about 15 to 20 were wrong or too broad (`ROUGE` with `Rouge-X`, `Step Verifier`
  with `verifier`, `bandit feedback` with `simulated bandit feedback`, `WorldTreeQA` with
  `WorldTreeV2`). A model "same" now stands only when one name is an acronym of the other or
  the names differ by nothing but generic words, plurals or word order. That left 52 merges; I
  read all 52 and nearly all look right (RGF, DPR, ILP, beam search, MHQA, ODQA). Cost: some
  correct merges are lost (`claude` with `claude-v1`), by design: a wrong merge hurts more than
  a missed one.
- This is my reading only, not a measurement. The real number comes from the labeled pairs in
  step 9 (gate: ER F1 at least 0.85).
- Money spent in Phase 2 so far: about **$2.40** of the $3 cap (extraction $2.24, resolution
  runs $0.16). The guard cost nothing.

## Step 7: Neo4j load (2026-10-24, Claude, built and run for real)

- Code: `pipeline/graphlens_pipeline/graphstore.py`, schema scripts in `graph_schema/`
  (`V001` unique entity id, `V002` type/name/version indexes + full-text, `V003` 768-d cosine
  vector index), CLI `graph-load` (resolves with the cached judge answers, then loads).
  The `neo4j` driver 5.28.2 is pinned; compose passes `NEO4J_*` to the `pipeline` service.
- Real run on `idx2-full-g0`: 1,848 entities (Author 128, Dataset 301, Method 940,
  Organization 70, Paper 179, Task 230) and 2,695 relations in Neo4j, equal to the resolution
  output; every entity has an embedding; no entity without source units, no edge without
  evidence units. Took 196 s, no model cost.
- Loading is idempotent (MERGE by stable id; a reload removes only that index version's own
  leftovers). 9 tests in `tests/test_graphstore.py`; 4 of them run against the real Neo4j.
- **Known problem for step 8:** 323 of 1,848 entities (17.5%) have no edge at all. The gate
  allows at most 10%, so this will fail unless the cause is fixed or the gate result is
  reported as a miss. I have not looked at which types they are yet.

## Step 8: quality report (2026-10-24, Claude, measured on the real graph)

- Code: `quality.py`, CLI `quality-report` (no model, no cost), results stored in
  `quality_checks`, report in `QUALITY.md`. 7 tests in `tests/test_quality.py`.
- PASS: schema validity 100%, node provenance 100%, edge evidence 100%, ontology conformance
  100%, embedding coverage 100%, duplicate proxy 2.9% (automatic, not the owner's audit).
- **MISS: orphan entities 17.5%** (323 of 1,848; target at most 10%).
- **Cause (checked on the raw extraction):** the model proposes entities that have no relation in
  the same text unit. 805 of 4,591 mentions (17.5%) are like that: cited papers (25% of Paper
  mentions), generic tasks and metrics such as "F1 score" (34% of Task mentions) and
  organizations (34%). 298 of the 323 isolated entities were mentioned only once. The load did
  not create them. The second check also dropped 573 of 4,184 proposed relations (13.7%).
- Not measured yet (need the labeled sets of step 9): relation precision, entity-resolution F1,
  and the owner's duplicate audit.

## Things that went wrong and were fixed (so the next session knows)

- `uv sync` in the image build failed because the connection dropped. The Dockerfile now has a
  download cache mount, system certificates, fewer parallel downloads and 5 tries.

- The first resolution run took 25+ minutes because model calls were one after another. I made
  them parallel. A reboot had also stopped Docker; starting Docker Desktop again fixed it.

- Docker's engine was stopped after a reboot. Quitting Docker Desktop, running `wsl --shutdown`
  and starting Docker Desktop again fixed it.
- I loaded evaluation set version 2 once before the remap had succeeded, so it held old unit
  IDs. I noticed, deleted only version 2 (no results pointed to it) and loaded it again after
  the remap and a passing `eval-verify`.

## Blockers

None.

## Decisions waiting for the owner

- OpenAI monthly limit of about $5 or more in the OpenAI dashboard (PREREQUISITES item 3).
- **Orphan entities (17.5%, target 10%).** Options: (A, my recommendation) keep them and report the
  miss, because an isolated entity still links a name to its text units for entity search, and
  the lever is a better extraction prompt in Phase 3; (B) leave isolated single-mention
  entities out of the graph, which would show about 1% but loses those links; (C) re-extract
  with a prompt that asks for a relation for every entity, which costs about $0.8 or more and
  would pass the $3 cap (about $2.40 is spent).

## Exact next action

Build step 9: the labeled sets (30 text units for relation precision and candidate pairs for
entity resolution, AI draft, then the owner reviews, about 2 hours), then step 10 (tests, docs,
README, CI, WALKTHROUGH). Nothing from Phase 2 is pushed.

## Notes for the next session

- Run everything through Docker; repository folder:
  `C:\Users\ACER\Downloads\Advanced GraphLens\Adavanced-GraphLens-`.
- `docker compose up -d --wait` starts the stack; `docker compose run --rm pipeline ...` runs
  the commands. Qdrant also holds unrelated sample collections (`dinosaurs` and others); they are
  not ours.
