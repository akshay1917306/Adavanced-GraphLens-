# Phase 5 status

Last updated: 2026-10-26

## State

**Plan approved by the owner; build in progress (steps 1 and 2 done, step 3 next).** Branch `phase-5/api-ui` from `main`
at a9748ef. Nothing pushed.

## Completed

- Phase 4 checkpoint (PR #5, tag `phase-4`) and the local-model option (PR #6).
- Plan approved: D42 to D48 and CR-0001, no OpenAI calls, no model download, fixtures.

## Built so far

- Step 1: `POST /api/v1/ask`, schemas, uniform error shape, CORS for the web origin only.
- Step 2: answers, traces and feedback stored in the existing tables (one anonymous local
  visitor until Phase 6); `POST /api/v1/feedback`; `GET /api/v1/status` with `X-Admin-Key`
  (off when `ADMIN_API_KEY` is empty). If saving fails the answer is still returned with `saved: false`.
- Checked in Docker: `ruff` clean, 30 API tests pass (including a real-Postgres store test on a
  temporary database). CI not run yet.
- Open risk: the pipeline and API packages have different dependency pins (neo4j 5.28 vs 6.4,
  FastAPI); decide before a live mode.

## Blockers

None.

## Decisions waiting for the owner

None.

## Exact next action

Step 3: replay service with real saved answers and passages, fixture mode wiring, more tests.
