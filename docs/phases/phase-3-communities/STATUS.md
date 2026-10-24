# Phase 3 status

Last updated: 2026-10-24

## State

**Built, waiting for the owner's review.** Everything in the plan is built and run except the
10-query cost and latency benchmark (needs the owner's yes) and the owner's two review samples.
Local branch `phase-3/communities`, branched from `main` at 6409007 (tagged `phase-2`, merged as
PR #3). Nothing from Phase 3 is pushed.

## Completed

- Phase 2 checkpoint finished earlier: PR #3 merged, CI green, tag `phase-2` pushed and verified.
- Plan approved by the owner (D27 to D32, cap $2.00, 10 more global questions), 2026-10-24.
- Step 1: `graspologic-native` 1.3.1 runs on the real graph; same seed, same result.
- Step 2: `communities.py`, schema `V004`, command `communities`: **193 communities** (level 0: 55,
  level 1: 117, level 2: 21), 55 stubs, hierarchy check clean (D33).
- Steps 3 and 4: `reports.py`, command `community-reports`. Full run (owner said yes, cap $0.75):
  **193 of 193** reports, no failure, **$0.2224** (estimate $0.25).
- Step 5: reports embedded into a Neo4j vector index (`V005`); gate checks
  `community_assignment`, `communities_with_report`, `report_citations_valid`,
  `report_embedding_coverage` all **100%**.
- Step 6: `globalsearch.py`, command `global-ask` (D34). One real question: ten themes from 22
  reports, 11.5 s, $0.006.
- Step 7: owner reviewed and approved the 10 extra global questions G11 to G20 ("all OK").
- Step 8: `globaleval.py`, command `global-eval`. Owner said run it. Result on 20 questions,
  order swapped: **comprehensiveness 100%, diversity 100%, empowerment 100%, directness 45%**
  (interval 84% to 100% for the first three). Without selection (first 10 questions): 100% on the
  first three, directness 40%. Cost $0.2623 plus $0.0297 to redo five items after internet
  time-outs. The win rates are stored in `quality_checks`.
- Step 9: `reviewsheets.py`, command `review-sheets`: `REVIEW_COMMUNITIES.md` (20 communities to
  rate) and `REVIEW_VERDICTS.md` (10 questions to check).
- Docs: BRIEF, PREREQUISITES, CHECKLIST, WALKTHROUGH, README, DECISIONS (D27 to D34).
- Tests: 305 pass, `ruff` clean (locally in Docker). CI has not run on GitHub.
- **Phase 3 spend: about $0.53 of the $2.00 cap** (reports $0.2224, report test $0.0062, two test
  questions $0.0074, evaluation $0.2920).

## Blockers

None.

## Decisions waiting for the owner

- A yes for `global-bench` (10 fresh global searches with selection, about $0.08, and 10 without,
  about $0.15) to measure cost and speed per query and the cost of skipping selection.
- Ratings for the 20 communities and a check of 10 judge verdicts (about 30 minutes).
- Accept the win-rate result with its caveats (answers are 3.4 times longer; the judge is the same
  model family; 20 questions).
- OpenAI monthly limit of about $5 or more (open since Phase 2).

## Exact next action

After the owner's yes: `global-bench` (with and without `--no-dynamic`), record the numbers in
CHECKLIST and WALKTHROUGH. After the owner's ratings: add them to the checklist. Then, on "Phase 3
approved": push `phase-3/communities`, open the pull request, check CI, merge, tag `phase-3`.

## Notes for the next session

- Run everything through Docker; repository folder:
  `C:\Users\ACER\Downloads\Advanced GraphLens\Adavanced-GraphLens-`.
- `docker compose up -d --wait` starts the stack. `graph-load` rebuilds the Neo4j graph from the
  cached extraction at no cost; then `communities`, `community-reports` (cached), `community-embed`.
- Git Bash rewrites `/out`-style paths and breaks on long here-documents with quotes; use
  PowerShell for `docker compose run -v ...` commands and write long scripts to a file first.
- The network to PyPI, GitHub and OpenAI drops now and then; finished work is cached, so run the
  same command again.
- `global-eval` prints only the cost of the run it just did; the totals are in this file.
