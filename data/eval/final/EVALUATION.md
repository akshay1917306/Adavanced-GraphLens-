# Final evaluation (Phase 7)

Run on 2026-10-29. Model `gpt-4.1-mini` for answers and for the judge (same family, so correctness is indicative, not independent). Written by a script from the measured results; nothing here is typed by hand. Questions: 30 hard and 30 easy local questions, 20 relate pairs, 10 development and 10 fresh unanswerable questions, a labeled router set; sets are small, so read the intervals.

## Targets

| Measure | Result | Target | Status |
|---|---|---|---|
| Local correctness, hard set (30 questions) | 70% (21 of 30, 95% interval 52% to 83%) | at least 75% | **missed** |
| Gap over plain RAG, hard set | +13.3 points (plain RAG 57%) | at least +15 points | **missed** |
| Citation support (judge, sample of answers) | 99.1% (114 of 115 claims, 20 answers) | at least 90% | met |
| Refusal on the 10 development unanswerable questions | 100% (10 of 10; the guards were tuned on this set) | at least 90% | met |
| Refusal on 10 fresh probes (not used for tuning) | 90% (9 of 10) | at least 90% | met |
| Router accuracy (rules, then the small model when unsure) | 97% (97 of 100; the model was asked 9 times) | at least 85% | met |
| Cost per local answer | $0.0031 on average, $0.0033 at most | at most $0.03 | met |
| Time per local answer, p95, one question at a time | 10.3 s (median 5.4 s, max 26.6 s, 60 questions) | at most 8 s | **missed** |

## Targets that were missed

- Local correctness, hard set (30 questions)
- Gap over plain RAG, hard set
- Time per local answer, p95, one question at a time

## Easy local set (30 questions, answers needing one passage)

Local search 29 of 30 correct (97%); plain RAG 28 of 30 (93%). This set was drafted from abstracts; the ceiling is 100% and plain RAG is already high.

## Relate mode (20 entity pairs)

A path was found for 20 of 20 pairs and had the expected length for 20. The expected paths came from the same graph, so this is a consistency check. Explanations written: 20; passed the citation check as verified: 14 of 20.

## Global search (carried over from Phase 3, not re-run)

Win rate against plain RAG over 20 questions, both answer orders must agree: comprehensiveness 100%, diversity 100%, empowerment 100%, directness 45%. The global code did not change after that run. The answers were 3.4 times longer than the baseline's, which favours the criteria above.

## Notes and limits

- Local answers were produced one at a time so the times are real; plain RAG ran three at a time.
- The retrieval part alone does about 2 to 3 questions per second per process (LOAD_TEST.md); ten people asking at the same moment would be slower than these times.
- Every system got a new name for this run, so no earlier answer was reused.
- The hard and easy sets were drafted by Claude and their review pages are still waiting for the owner; the judge is the same model family as the answerer.
- The refusal guards were designed after looking at the development unanswerable questions, so that number is not independent; the fresh probes were not used for tuning.
- The relate paths were found in the same graph the expected paths came from.

Cost of this run: $0.3206.
