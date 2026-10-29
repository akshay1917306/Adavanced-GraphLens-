# Phase 7 status

Last updated: 2026-10-29

## State

**Plan approved by the owner on 2026-10-29; build in progress (steps 1 to 3 done; step 4 built, waiting for the owner's yes to the paid run).** Branch `phase-7/launch` from `main` at 667addc
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
  92%). Correction made later: `route-eval` does use the entity index, it simply had no labeled
  question that contains the task name "link prediction", so it could not see this error; the final
  evaluation labels include such questions (the hard set).
- **Logging gap, fixed.** The search service printed no request lines; it now logs request id, mode,
  status and time (never the question), and the API's request id travels with the call.
- **Latency:** 6.6 s for one local question, close to the 8 s p95 target; the real number comes from
  the final evaluation.
- The router model (used when the rules are unsure) was exercised for the first time: it sent an
  out-of-corpus question to plain RAG, which refused correctly.

After the test the stack was put back to replay mode (`search` stopped), so nothing spends money by
accident. To run live: set `ANSWER_MODE=live` in `.env` and `docker compose --profile live up -d --build`.

## Step 2: reliability

- Search service: at most 4 questions run at once; a request waits up to 5 s for a slot and is then
  told "busy" (503); a question running longer than 40 s gets 504 and **keeps its slot until it really
  ends**, so a stuck question cannot pile up. Free reads (local-search retrieval, global selection,
  text lookups) are retried twice with back-off (0.2 s, 0.6 s); relate path search and plain-RAG
  retrieval are not wrapped yet. The model client is behind a circuit breaker (5 failures, 30 s pause)
  and its timeout is tighter in the service (30 s, one client retry). A model call is never repeated.
- API: a 504 from the service becomes the same "took too long" 504 (`engine_timeout`).
- Tests with fakes: pipeline 441 pass (11 new: retry, breaker, guarded model, slots and deadline),
  API 150 pass (2 new). Ruff clean on both.
- **Live test of the cost cap and the rate limit** (owner's yes, estimate $0.006, cap $0.02; run
  with a cap of $0.0100 per day and 3 asks per minute): ask 1 and 2 answered with real model calls
  ($0.0031 and $0.0029); ask 3 was refused `daily_limit` and ask 4 `rate_limited`, and **neither
  reached the search service** (checked in its log), so no money was spent on them. The Redis daily
  counter ended at $0.011456, which equals the three real spends of the day. The key never appeared
  in the API or search logs (searched). Real spend of this test: $0.0060. Afterwards the stack went
  back to replay mode with the normal limits (10 asks per minute, cap $1.00).
- **Latency observation:** the two local questions took 6.2 s and 9.2 s inside the service, so the
  p95 target of 8 s is at risk; it is measured properly in the final evaluation.

Phase 7 spend so far: about **$0.0114** of the $3.00 cap.

## Step 3: fixes and measurements (owner's yes, cap $0.50, spent $0.2906)

Details and tables: `EXPERIMENTS.md`; raw results in `data/eval/phase7/results/`.

- **Refusal:** development unanswerable questions 8 of 10 (Phase 4) to **10 of 10** (tuned on that
  set); 10 fresh, untuned probes **9 of 10**. Three guards: a plain-word name alone is not enough,
  a version number the papers do not know ("Claude 2") is refused before the model, and a refusal
  in plain words becomes a refusal. 0 of the 60 answerable development questions are blocked.
  Still failing: F03 (an invented "technical report" conclusion). A stricter prompt was tried and reverted.
- **Relate explanations:** all 9 warnings came from the "entity not in context" heuristic firing on
  weak names and junk entities (0 cited a missing label); after the fix the same saved texts give
  17 of 20 verified. They were re-checked, not regenerated, and not read by anyone for faithfulness.
- **Context size:** 8,000 tokens 20 of 30 (new prompt) vs 12,000 tokens 22 of 30 vs Phase 4's 21 of 30:
  no clear gain, +38% cost, three times the warnings: **keep 8,000** (D67, D68). The 75% target stays missed.
- Tests: pipeline 461 pass, API 150 pass; ruff clean on both.
- Found while doing this: the Phase 4 refusal measurement counted only the exact marker, so plain-words
  refusals looked like answers; the cache key of the correctness runner ignores the prompt and the
  context size, so a variant must get its own system name (done).

Phase 7 spend so far: about **$0.30** of the $3.00 cap.

## Step 4: final evaluation (built, not run)

`final-eval` (command) and `finaleval.py` (report generator, 10 tests) write the final numbers to JSON
and `docs/EVALUATION.md` by script. Every system gets a new name (`final_*`), so no earlier answer is
reused. Parts: local and plain RAG on the 30 hard and the 30 easy questions (local one at a time for
real timings), citation support on a sample of 20 answers, refusal on the 10 development and the 10
fresh questions, relate on 20 pairs, the router with its model step and the entity index on 100
labeled questions, and the Phase 3 global result carried over (global code is unchanged). Dry run:
**$0.41, $0.57 with a 40% margin**, cap $0.60; nothing was spent. Tests: pipeline 471 pass, ruff clean.

## Blockers

None.

## Decisions waiting for the owner

None. The owner will set the OpenAI monthly limit to $10 and put the key into `.env` before the first live test.

## Exact next action

Run `final-eval` after the owner's yes (about $0.41, cap $0.60); copy the generated page to `docs/EVALUATION.md`; then step 5 (owner review pages and spot-check).
