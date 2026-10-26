# Phase 4 status

Last updated: 2026-10-26

## State

**Requirements step: plan written, waiting for the owner's approval.** Nothing is built. Local
branch `phase-4/local-search`, branched from `main` at ce6f4de (tagged `phase-3`, merged as PR #4).
Nothing from Phase 4 is pushed.

## Completed

- Phase 3 checkpoint finished: PR #4 merged, CI green on the branch commit and on `main` (all four
  jobs), tag `phase-3` pushed and verified (remote and local both point to ce6f4de).
- `BRIEF.md`, `PREREQUISITES.md`, `CHECKLIST.md`, `PROMPT.md` written. The owner asked to keep
  the OpenAI spend low, so the plan was cut to a $0.80 cap with free measurements wherever
  possible (2026-10-26). Blueprint section 2.6
  (query pipeline) and the targets in 1.2 were read for the plan.

## Blockers

None for the plan. One problem is written down in the brief: the baseline already gets 93% on
the local questions we have, so "15 points above baseline" needs a harder set (D35).

## Decisions waiting for the owner

- D35 to D40 in `BRIEF.md` (harder local set, PageRank in numpy, router, new evaluation sets,
  citation check, models and the **$0.80** cap).
- OpenAI monthly limit: $5 is enough (this month's spend is about $3.3).

## Exact next action

After the owner approves: build step 1, the sanitiser and entity linking, tested on the real
graph. No paid model call before the dry-run estimate and the owner's yes.

## Notes for the next session

- Run everything through Docker; repository folder:
  `C:\Users\ACER\Downloads\Advanced GraphLens\Adavanced-GraphLens-`.
- `docker compose up -d --wait` starts the stack; the Phase 3 commands (`communities`,
  `community-reports`, `community-embed`) rebuild the community layer from cache at no cost.
- Git Bash rewrites `/out`-style paths and breaks on long here-documents with quotes; use
  PowerShell for `docker compose run -v ...` commands and write long scripts to a file first.
- The network to PyPI, GitHub and OpenAI drops now and then; finished work is cached, so run the
  same command again.
