# Phase 7 status

Last updated: 2026-10-29

## State

**Plan approved by the owner on 2026-10-29; build in progress (step 1 done, step 2 next).** Branch `phase-7/launch` from `main` at 667addc
(Phase 6 tagged `phase-6`, placeholder fix merged). Nothing pushed.

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

## First live smoke test (2026-10-29, owner's yes, cap $0.05)

The search container started healthy, the API ran with `ANSWER_MODE=live`, and three real questions
went through the whole path (API, search service, router, databases, model, citation check, saving).

| Question | Route | Result | Cost |
|---|---|---|---|
| KGT5 model size and the two graphs (compare on) | rules said **relate** (wrong) | answered, citation check `warning`; the plain-RAG answer beside it was `verified` and complete | $0.0018 |
| How is KGT5 connected to Wikidata5M? | relate | answered, `verified`, graph with 2 nodes and 1 link | $0.0005 |
| Capital of France | the router model chose plain RAG | refused: "not enough evidence" | $0.0001 |
| The first question again, after the fix below | rules said **local** | answered, `verified`, 6 sources, graph with 6 nodes and 8 links, 6.6 s | $0.0031 |

Total spent: **$0.0054** (estimate was $0.01). The key never appeared in the API or search logs
(searched). The daily cost counter in Redis was created, so the cap sees real spend.

Findings:
- **Router bug, fixed.** The rule treated the word "link" as a relate cue, so any question about
  "link prediction" (a task name) went to relate mode. The cue now needs "link to / with / between"
  and 6 regression tests cover it (430 pipeline tests pass; the rules-only evaluation is unchanged at
  92%, which also shows that evaluation runs without the entity index and cannot see this class of
  error: the final evaluation must run the router with the index).
- **Logging gap, fixed.** The search service printed no request lines; it now logs request id, mode,
  status and time (never the question), and the API's request id travels with the call.
- **Latency:** 6.6 s for one local question, close to the 8 s p95 target; the real number comes from
  the final evaluation.
- The router model (used when the rules are unsure) was exercised for the first time: it sent an
  out-of-corpus question to plain RAG, which refused correctly.

After the test the stack was put back to replay mode (`search` stopped), so nothing spends money by
accident. To run live: set `ANSWER_MODE=live` in `.env` and `docker compose --profile live up -d --build`.

## Blockers

None.

## Decisions waiting for the owner

None. The owner will set the OpenAI monthly limit to $10 and put the key into `.env` before the first live test.

## Exact next action

Step 2: per-request time limit and retries for Neo4j and Qdrant inside the search service, exercise the cost cap and rate limits with real calls (a few cents, with a shown estimate first).
