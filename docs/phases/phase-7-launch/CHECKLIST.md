# Phase 7 acceptance checks

Mark an item only after it was run, and say where it was run. A missed target is reported, not hidden.

## Live answers and reliability

- [x] Change request for D61 written and approved; D43 marked as amended
      **Result:** `docs/adr/CR-0004-separate-search-service.md`, approved with the plan on 2026-10-29.
- [ ] Internal search service runs from the pipeline image; the API calls it; no dependency conflict
      Partly: code and 49 tests with fakes pass in Docker; the container has not been started and no live call made.
- [ ] Live answer on the screen: sources, graph, citation badge, refusal and clarify
- [ ] Per-request time limit; retry with back-off for Neo4j and Qdrant; model-call circuit breaker (tested with fakes)
- [ ] Daily cost cap and rate limits exercised with real calls
- [ ] The OpenAI key never appears in logs, responses, the web bundle or git (searched)

## Fixes

- [ ] Refusal: generic words and model names no longer link to an unrelated entity (checked on the unanswerable set)
- [ ] The 9 relate explanations that failed the citation check are diagnosed (cause written down)
- [ ] Context size 8,000 vs 12,000 tokens measured on the hard set (cost and correctness)

## Final evaluation (one clean run, written to `docs/EVALUATION.md`)

- [ ] Local correctness on the hard set (target at least 75% and at least 15 points over baseline)
- [ ] Local correctness on the easy set
- [ ] Global win rate with the caveats stated (length, same-family judge, set size)
- [ ] Relate: path correctness and explanation citation check on 20 pairs
- [ ] Refusal accuracy on the unanswerable set (target at least 90%)
- [ ] Router accuracy including its model step (target at least 85%)
- [ ] Citation support on a sample (target at least 90%)
- [ ] End-to-end p95 and cost per local query over sequential live queries (targets 8 s and $0.03)
- [ ] Total Phase 7 spend within the $3.00 cap
- [ ] Every target that is missed is listed with its reason in the README

## Owner review

- [ ] Phase 3 community ratings and judge verdicts reviewed
- [ ] Phase 4 review pages reviewed
- [ ] Spot-check of 10 citations and 10 judge verdicts done

## Operations and release

- [ ] Backup scripts for Postgres, Neo4j and Qdrant
- [ ] A restore was actually performed on a clean stack and the app answered afterwards
- [ ] Runbook: start, stop, health, backup, restore, common errors
- [ ] One-command start works from a fresh clone (README steps only)
- [ ] `ruff`, `pytest`, `tsc`, `eslint`, `next build` pass; CI green (including the new service)
- [ ] README final; architecture page; 3-minute demo script; interview page; known limits
- [ ] WALKTHROUGH.md, STATUS.md, DECISIONS.md updated
- [ ] Owner approved; tags `phase-7` and `v1.0`
