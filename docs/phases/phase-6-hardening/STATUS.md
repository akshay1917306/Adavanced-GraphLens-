# Phase 6 status

Last updated: 2026-10-27

## State

**Plan approved by the owner on 2026-10-27; build in progress (steps 1 and 2 done).** Branch
`phase-6/hardening` from `main` at 0593c11 (Phase 5 tagged `phase-5`). Nothing pushed.

## Completed

- Phase 5 checkpoint: PR #7 and the docs PR #8 merged, CI green, tag `phase-5`.

## Built so far

- The Phase 5 test rows of the `local-demo` visitor were deleted (owner's choice): 1 visitor,
  9 conversations, 3 ratings. Rows made later by the Phase 6 checks below are also test rows.
- Step 1: signed visitor token (`api/app/visitor.py`), `POST /api/v1/visitor`, ask and feedback
  need a valid token (deny by default), feedback checks that the answer belongs to the visitor,
  the web proxy keeps the token in an `HttpOnly`, `SameSite=Lax` cookie and renews it when it is
  missing, forged or unknown, and only accepts JSON posts. `VISITOR_TOKEN_SECRET` was generated into
  the git-ignored `.env`; `.env.example` has a placeholder.
- Checked: 65 API tests pass in Docker (token round trip, tampered, wrong secret, expired, wrong
  visitor, forged cookie, store-level ownership on a temporary Postgres), ruff clean, eslint and
  tsc clean. By hand with curl against the running stack: a second visitor gets "No such answer"
  for the first visitor's answer, the owner can rate it, a forged cookie is replaced by a new
  visitor, non-JSON posts and direct API calls without a token are refused; the cookie is not
  readable from page JavaScript; the screen still works.
- Step 2 (API only; the screen comes in step 4): `GET /api/v1/history`, `GET` and `DELETE
  /api/v1/history/{id}`, `DELETE /api/v1/me` (deletes the visitor and everything under them, returns
  the counts), `GET`, `POST` and `DELETE /api/v1/saved`, `GET` and `PUT /api/v1/preferences`.
  Every query is limited to the visitor's own rows and returns "not found" for anything else;
  every route refuses a missing or forged token. History shows question, answer text, mode, check
  status and rating; the passages and graph are not stored (no schema change), so an old answer
  cannot be re-opened with its sources.
- Checked: 90 API tests pass in Docker (two-visitor tests on a temporary Postgres: privacy of
  history, saved answers and preferences, hard delete of one conversation and of everything,
  other visitor untouched), ruff clean. By hand with curl on the running stack: the second visitor
  cannot open, delete or save the first visitor's rows; delete-all removes the visitor and the old
  token stops working.
- Test rows from these curl checks (a few visitors and conversations) are in the local database;
  they are cleaned at the end of the phase.
- Known gap until step 5: `POST /api/v1/visitor` can create visitors without limit (rate limits
  come in step 5).

## Blockers

None.

## Decisions waiting for the owner

- D51 to D58 in `BRIEF.md` (D55 and D58 change earlier notes: no Prometheus or Grafana, live
  answers wait for Phase 7).
- What to do with the Phase 5 test rows of the `local-demo` visitor.

## Exact next action

Step 3 is already covered by step 2's tests; next is step 4 (screen: history, delete with confirmation, save, preferences), then step 5 (rate limits and cost cap).
