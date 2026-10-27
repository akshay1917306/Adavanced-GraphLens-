# Phase 6 status

Last updated: 2026-10-27

## State

**Plan approved by the owner on 2026-10-27; build in progress (step 1 done).** Branch
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
- Known gap until step 5: `POST /api/v1/visitor` can create visitors without limit (rate limits
  come in step 5).

## Blockers

None.

## Decisions waiting for the owner

- D51 to D58 in `BRIEF.md` (D55 and D58 change earlier notes: no Prometheus or Grafana, live
  answers wait for Phase 7).
- What to do with the Phase 5 test rows of the `local-demo` visitor.

## Exact next action

Step 2: history list, open one, delete one, delete all, saved answers and preferences (API and tests).
