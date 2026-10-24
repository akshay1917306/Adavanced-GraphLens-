# Phase 3 status

Last updated: 2026-10-24

## State

**Requirements step: plan written, waiting for the owner's approval.** Nothing is built. Local
branch `phase-3/communities`, branched from `main` at 6409007 (tagged `phase-2`, merged as
PR #3). Nothing from Phase 3 is pushed.

## Completed

- Phase 2 checkpoint finished: PR #3 merged, CI green on the branch commit (all four jobs),
  tag `phase-2` pushed and verified (remote and local both point to 6409007).
- Measured the graph shape for the plan: 1,545 entities, 2,694 edges, 96% of entities in one
  connected component, 25 isolated entities, 10 tiny groups (2 to 7 entities), hubs with degree
  56 to 75.
- `BRIEF.md`, `PREREQUISITES.md`, `CHECKLIST.md`, `PROMPT.md` written.

## Blockers

None for the plan. The build needs the owner's decisions below.

## Decisions waiting for the owner

- D27 to D32 in `BRIEF.md` (Leiden edges, library, tiny communities, model, judge and sample
  size, spend cap of $2.00), and whether to add 10 more global questions.
- OpenAI monthly limit of about $5 or more (open since Phase 2).

## Exact next action

After the owner approves: build step 1, the install test of the Leiden library in the image
(D28) on the real graph. No paid model call before the dry-run estimate and the owner's yes.

## Notes for the next session

- Run everything through Docker; repository folder:
  `C:\Users\ACER\Downloads\Advanced GraphLens\Adavanced-GraphLens-`.
- `docker compose up -d --wait` starts the stack. `graph-load` rebuilds the Neo4j graph from the
  cached extraction at no cost. Git Bash rewrites `/out`-style paths; use PowerShell for
  `docker compose run -v ...:/out` commands.
- The network to PyPI and GitHub is flaky on this machine; the Dockerfile has retries and a
  download cache for `uv sync`.
