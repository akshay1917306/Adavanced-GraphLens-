# Phase 3 status

Last updated: 2026-10-24

## State

**Build in progress, step 8 of 9: everything except the paid global evaluation is built.**
Local branch `phase-3/communities`, branched from `main` at 6409007 (tagged `phase-2`, merged as
PR #3). Nothing from Phase 3 is pushed.

## Completed

- Phase 2 checkpoint finished: PR #3 merged, CI green on the branch commit (all four jobs),
  tag `phase-2` pushed and verified (remote and local both point to 6409007).
- Measured the graph shape for the plan: 1,545 entities, 2,694 edges, 96% of entities in one
  connected component, 25 isolated entities, 10 tiny groups (2 to 7 entities), hubs with degree
  56 to 75.
- `BRIEF.md`, `PREREQUISITES.md`, `CHECKLIST.md`, `PROMPT.md` written. Owner approved the plan
  and D27 to D32, cap $2.00, and 10 more global questions (2026-10-24).
- Step 1: `graspologic-native` 1.3.1 (Leiden core of graspologic) installs and runs on the real
  graph; same seed gives the same result.
- Step 2: `communities.py`, schema `V004`, command `communities`. Real graph: **193 communities**
  (level 0: 55, level 1: 117, level 2: 21), 55 stubs, hierarchy check clean, a second write gives
  the same graph. D33 records the settings (seed 42, max cluster size 50).
- Steps 3 and 4 (code): `reports.py` and command `community-reports`. Leaf communities are
  described by their top entities and relationships, split communities by their children's
  reports (bottom-up), tiny ones get a stub without a model. Citations outside the shown
  evidence are removed; cache by prompt hash; cost cap. Smoke test of 3 real reports: coherent,
  citations valid, $0.0062 for 3 calls.
- Full report run (owner said yes, cap $0.75): **193 of 193 communities have a report** (135 new,
  3 cached, 55 stubs), no failure, **$0.2224**. Smoke test before it: $0.0062.
- Step 5: reports embedded with the local bge model into a Neo4j vector index (`V005`). Gate
  checks `community_assignment`, `communities_with_report`, `report_citations_valid` and
  `report_embedding_coverage` are all **100%**.
- Step 6: `globalsearch.py` and command `global-ask`: dynamic selection (at most 40 reports,
  leaf-aware level cover, stubs excluded), parallel map batches, reduce with [C1] citations,
  progress events, partial failure. A real run on G01: ten themes from 22 reports, 11 s, $0.006.
  A first map batch failed because the output limit (1,200 tokens) cut the JSON; the limit is now
  3,000 and a failed batch still counts its cost. Similarity scores are bunched (0.79 to 0.82),
  so the top 40 by rank does the selecting and the threshold stays at 0.
- Step 7: 10 extra global questions G11 to G20 in `data/eval/v0/global_extra.json` (quotes
  verified, 0 problems) with `REVIEW_EXTRA.md`. **Not yet reviewed by the owner.**
- Step 8 (code): `globaleval.py` and command `global-eval` (pairwise judge, order swapped, four
  criteria, cache, cost cap, ablation without selection). **Dry-run estimate: about $0.46 (about
  $0.65 with margin)**; not run yet.

## Blockers

None.

## Decisions waiting for the owner

- A yes for the global evaluation run (about $0.46, cap $1.00).
- The owner's review of the 10 extra global questions (`REVIEW_EXTRA.md`, about 30 minutes).
- OpenAI monthly limit of about $5 or more (open since Phase 2).

## Exact next action

After the owner's yes: `global-eval --max-cost-usd 1.0` with the results folder mounted, then
step 9 (review sheets: 20 communities and 10 judge verdicts for the owner), then docs, tests,
README, WALKTHROUGH and the A to J report. No paid batch without the owner's yes.

## Notes for the next session

- Run everything through Docker; repository folder:
  `C:\Users\ACER\Downloads\Advanced GraphLens\Adavanced-GraphLens-`.
- `docker compose up -d --wait` starts the stack. `graph-load` rebuilds the Neo4j graph from the
  cached extraction at no cost. Git Bash rewrites `/out`-style paths; use PowerShell for
  `docker compose run -v ...:/out` commands.
- The network to PyPI and GitHub is flaky on this machine; the Dockerfile has retries and a
  download cache for `uv sync`.
