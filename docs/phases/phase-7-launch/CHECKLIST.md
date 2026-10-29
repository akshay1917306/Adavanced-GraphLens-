# Phase 7 acceptance checks

Mark an item only after it was run, and say where it was run. A missed target is reported, not hidden.

## Live answers and reliability

- [x] Change request for D61 written and approved; D43 marked as amended
      **Result:** `docs/adr/CR-0004-separate-search-service.md`, approved with the plan on 2026-10-29.
- [x] Internal search service runs from the pipeline image; the API calls it; no dependency conflict
      **Result:** started healthy from the pipeline image; 4 live questions through the API worked (see STATUS); 430 pipeline and 148 API tests pass.
- [ ] Live answer on the screen: sources, graph, citation badge, refusal and clarify
      Partly: the API returns sources, graph, badge and a refusal for live questions; the browser screen was not yet used in live mode and clarify was not seen.
- [x] Per-request time limit; retry with back-off for Neo4j and Qdrant; model-call circuit breaker (tested with fakes)
      **Result:** done with fakes (see STATUS step 2). A real timeout and a real database outage were not provoked live; relate and plain-RAG retrieval are not covered by the retry yet.
- [x] Daily cost cap and rate limits exercised with real calls
      **Result:** 2 real answers, then `daily_limit` and `rate_limited` with no call reaching the search service; Redis counter matched the spend ($0.0060 for the test).
- [ ] The OpenAI key never appears in logs, responses, the web bundle or git (searched)
      Partly: no key pattern in the API and search logs after the live test; web bundle and git were not searched again in this phase.

## Fixes

- [x] Refusal: generic words and model names no longer link to an unrelated entity (checked on the unanswerable set)
      **Result:** 10 of 10 on the development set (tuned there) and 9 of 10 on 10 fresh probes; F03 still invents an answer. See EXPERIMENTS.md.
- [x] The 9 relate explanations that failed the citation check are diagnosed (cause written down)
      **Result:** all 9 from the entity heuristic on weak and junk names, none from missing labels; 17 of 20 verified after the fix (re-checked, not regenerated).
- [x] Context size 8,000 vs 12,000 tokens measured on the hard set (cost and correctness)
      **Result:** 22 vs 20 of 30 (new prompt), within noise, +38% cost; 8,000 kept (D68).

## Final evaluation (one clean run, written to `docs/EVALUATION.md`)

- [x] Local correctness on the hard set (target at least 75% and at least 15 points over baseline)
      **Result: MISSED.** 70% (21 of 30), +13.3 points over plain RAG (57%). See EVALUATION_NOTES.md.
- [x] Local correctness on the easy set
      **Result:** 29 of 30 (plain RAG 28 of 30).
- [x] Global win rate with the caveats stated (length, same-family judge, set size)
      **Result:** carried over from Phase 3, not re-run: 100%, 100%, 100%, directness 45%.
- [x] Relate: path correctness and explanation citation check on 20 pairs
      **Result:** paths 20 of 20 (consistency check); explanations verified 14 of 20.
- [x] Refusal accuracy on the unanswerable set (target at least 90%)
      **Result:** 10 of 10 development (tuned there), 9 of 10 fresh probes.
- [x] Router accuracy including its model step (target at least 85%)
      **Result:** 97 of 100; the model was asked 9 times; 3 misses listed in EVALUATION_NOTES.md.
- [x] Citation support on a sample (target at least 90%)
      **Result:** 99.1% (114 of 115 claims, 20 answers).
- [x] End-to-end p95 and cost per local query over sequential live queries (targets 8 s and $0.03)
      **Result: p95 MISSED** at 10.3 s (median 5.4 s); cost met at $0.0031. Measured one at a time over 60 questions.
- [ ] Total Phase 7 spend within the $3.00 cap
      So far about $0.62 of $3.00; final figure at the end of the phase.
- [ ] Every target that is missed is listed with its reason in the README
      Listed with reasons in EVALUATION.md and EVALUATION_NOTES.md; the README is rewritten in the release step.

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
