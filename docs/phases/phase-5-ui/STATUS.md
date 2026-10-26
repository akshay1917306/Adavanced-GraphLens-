# Phase 5 status

Last updated: 2026-10-26

## State

**Plan approved by the owner; build in progress (steps 1 to 3 done, step 4 (web) next).** Branch `phase-5/api-ui` from `main`
at a9748ef. Nothing pushed.

## Completed

- Phase 4 checkpoint (PR #5, tag `phase-4`) and the local-model option (PR #6).
- Plan approved: D42 to D48 and CR-0001, no OpenAI calls, no model download, fixtures.

## Built so far

- Step 1: `POST /api/v1/ask`, schemas, uniform error shape, CORS for the web origin only.
- Step 2: answers, traces and feedback stored in the existing tables (one anonymous local
  visitor until Phase 6); `POST /api/v1/feedback`; `GET /api/v1/status` with `X-Admin-Key`
  (off when `ADMIN_API_KEY` is empty). If saving fails the answer is still returned with `saved: false`.
- Step 3: `export-replay` (pipeline, free) rebuilt 5 real saved local answers and 2 refusals
  with their passages and a small evidence graph; every entry is kept only if the rebuilt context
  still has every cited label and the same citation-check result (7 of 7 kept). Replay mode in the
  API (`ANSWER_MODE=replay`, default) serves them; other questions get a plain refusal. Also
  `GET /api/v1/examples`. Limits: only local mode and refusals are replayed (relate and global
  explanations were never saved); saved answers carry no cost or latency (shown as 0); node and
  link confidence is empty, so no dashed lines yet.
- Checked in Docker (steps 1 and 2): `ruff` clean, 30 API tests pass (32 after step 3) (including a real-Postgres store test on a
  temporary database). CI not run yet.
- Open risk: the pipeline and API packages have different dependency pins (neo4j 5.28 vs 6.4,
  FastAPI); decide before a live mode.

## Blockers

None.

## Decisions waiting for the owner

None.

## Exact next action

Step 4: the web Ask screen (Docker build for typecheck, lint and build).
