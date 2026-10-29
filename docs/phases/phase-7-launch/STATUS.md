# Phase 7 status

Last updated: 2026-10-29

## State

**Plan approved by the owner on 2026-10-29; build in progress (step 1).** Branch `phase-7/launch` from `main` at 667addc
(Phase 6 tagged `phase-6`, placeholder fix merged). Nothing pushed, no OpenAI call yet.

## Completed

- Phase 6 checkpoint: PR #9 and the docs PR #10 merged, all 6 CI jobs green, tag `phase-6`.

## Built so far

- CR-0004 (D61) written; D60 to D66 recorded in `DECISIONS.md`.
- Internal search service (`pipeline/graphlens_pipeline/searchservice.py`, command `serve-search`):
  `POST /search` (shared key, question up to 4,000 characters, `compare`) and `GET /healthz`. It
  routes the question (rules first, a small model only when unsure), runs the chosen mode (local,
  relate, global or plain RAG) and returns the same `Answer` shape the screen already uses, with
  sources, a small evidence graph and the citation check. Plain-RAG answers get `[T1]` labels so the
  screen shows chips. Logs carry request id, mode, status and time, never the question. It stops at
  start-up with a clear message when the shared key or the model key is missing.
- API side: `LiveService` (`api/app/live.py`) with a 45 s time limit (504 `engine_timeout`), one retry
  only when the connection could not be opened (never after the request was sent), a circuit breaker
  (5 failures, 30 s pause, one trial call), and a strict reply contract (an unknown field is refused).
  `ANSWER_MODE=live` selects it; the default stays `replay`. `/api/v1/examples` now also says
  `live`, and the screen changes its placeholder and label.
- Compose: service `search` under the profile `live` (not published on any port; only the API
  reaches it); `SEARCH_SERVICE_KEY` was generated into the git-ignored `.env`.
- Checked: pipeline 424 tests pass (24 new, with fakes), API 148 tests pass (25 new: breaker with a
  fake clock, contract, timeout not retried, connect retry once, breaker, 504 and 503 mapping), ruff,
  eslint, tsc and the web build pass, and replay mode still runs (`live: false`). **No real model call
  has been made in this phase yet.**
- Pipeline change that other code can see: `LocalContext.graph` and `RelateAnswer.context` are new
  optional fields (the service reads them); no behaviour changed.
- Not done yet: the first live smoke test, time limits and retries for Neo4j and Qdrant inside the
  search service, exercising the cost cap and rate limits with real calls, `uvicorn` declared
  explicitly in the pipeline lock file (it comes in through Prefect today).

## Blockers

The first live smoke test needs the owner's yes (a shown estimate) and confirmation that the OpenAI monthly limit is set to $10.

## Decisions waiting for the owner

None. The owner will set the OpenAI monthly limit to $10 and put the key into `.env` before the first live test.

## Exact next action

First live smoke test (estimate about $0.01, cap $0.05) after the owner's yes; then step 2.
