# Phase 3 status

Last updated: 2026-10-24

## State

**Build in progress, step 4 of 9: report generation is built and waits for the owner's yes
before the paid run.** Local branch `phase-3/communities`, branched from `main` at 6409007
(tagged `phase-2`, merged as PR #3). Nothing from Phase 3 is pushed.

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
- **Dry-run estimate for the full report run: 138 model calls, about $0.25 (about $0.33 with
  retries).**

## Blockers

None for the plan. The build needs the owner's decisions below.

## Decisions waiting for the owner

- D27 to D32 in `BRIEF.md` (Leiden edges, library, tiny communities, model, judge and sample
  size, spend cap of $2.00), and whether to add 10 more global questions.
- OpenAI monthly limit of about $5 or more (open since Phase 2).

## Exact next action

After the owner says yes to the report run: `community-reports` (cap $0.75), then build step 5
(embed the reports and create the Neo4j vector index). No paid batch without the owner's yes.

## Notes for the next session

- Run everything through Docker; repository folder:
  `C:\Users\ACER\Downloads\Advanced GraphLens\Adavanced-GraphLens-`.
- `docker compose up -d --wait` starts the stack. `graph-load` rebuilds the Neo4j graph from the
  cached extraction at no cost. Git Bash rewrites `/out`-style paths; use PowerShell for
  `docker compose run -v ...:/out` commands.
- The network to PyPI and GitHub is flaky on this machine; the Dockerfile has retries and a
  download cache for `uv sync`.
