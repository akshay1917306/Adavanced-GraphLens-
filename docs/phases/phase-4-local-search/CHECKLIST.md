# Phase 4 acceptance checks

Mark an item only after it was run, and say where it was run. Targets come from the blueprint;
the exit is "measured", so a missed target is reported, not hidden.

## Build

- [x] Sanitiser: at most 4,000 characters; keys, tokens and emails are redacted before anything
      is logged or sent
      **Result:** unit tests (mocked); not run on real traffic.
- [ ] Entity linking finds the right seed entities for the benchmark questions (measured; report
      the share where the expected entity is among the 5 seeds)
      **Result:** seed share not reported separately; the evidence ladder (linking only) reaches 75% of gold units on the hard set and 93% on the easy set.
- [x] Expansion uses one fixed, parameterised Cypher template; at most 200 candidates; no
      model-written Cypher anywhere
      **Result:** fixed template, 200 cap, tests pass.
- [x] Personalized PageRank in numpy is deterministic and keeps the top 60 nodes
      **Result:** deterministic, tests pass; it added no measurable evidence (95% to 95%).
- [x] Context respects the 8,000-token budget and its split; every item carries a `[T]`, `[E]`
      or `[C]` label
      **Result:** tests pass; real runs ran inside the budget.
- [x] Citation check: every cited ID exists in the context (100% of benchmark answers or the
      failures are listed); sentences naming entities that are not in the context are flagged;
      the result is `verified`, `warning` or `not_checked`
      **Result:** unit tests; 122 of 124 sampled citations were supported by the judge. Per-answer 100% label-exists not reported as a separate number.
- [x] Refuse when no seed is similar enough or the evidence is thin; ask when an entity is
      ambiguous
      **Result:** 8 of 10 refused; see Measured.
- [x] Relate mode: up to 3 paths of at most 4 hops, evidence for every hop, nearest shared
      communities when there is no path
      **Result:** 20 of 20 pairs gave a path of the right length; 11 of 20 explanations passed the citation check as verified.
- [x] Router: rules plus a model call; confidence under 0.6 runs local and says so; the mode can
      be forced
      **Result:** rules plus model call built; only rules measured (46 of 50 acceptable).
- [ ] Baseline mode gets the optional rerank (top 20 to 5)
      **Result:** NOT DONE: deferred, needs a new model download.
- [x] Dry-run estimate shown before each paid batch; the cost cap stops a run cleanly
      **Result:** dry run showed $0.36; the real run cost $0.267; the cap stops the run.

## Measured

- [ ] Local correctness on the hard multi-hop set: at least 75%, and at least 15 points above the
      baseline (report the number of questions and the interval)
      **Result:** MISSED the 75% bar: local 21/30 = 70% (interval 52 to 83%), baseline 53%; the gap is 16.7 points, so the 15-point margin is met. 9 wins, 19 ties, 2 losses.
- [ ] Local correctness on the easy set (ceiling 100%, baseline was 93%)
      **Result:** NOT RUN (no paid run, to save cost).
- [x] Ablations without any model call: the share of the evidence text units that reach the
      context with entity linking only, plus expansion, plus PageRank, plus community reports;
      model answers (correctness, cost, latency) only for baseline, local without community
      reports and full local
      **Result:** evidence ladder free (see STATUS); model answers: local and local-without-reports are identical (21/30 each), so community reports add nothing here.
- [x] Citation precision (a cited passage supports its claim): at least 90% by the judge on a
      sample of 20 answers, and the owner's spot-check of 10
      **Result:** 98.4% (122/124, 20 answers, same-family judge). Owner spot-check of 10 still to do.
- [ ] Refusal accuracy on 10 unanswerable questions: at least 90%
      **Result:** MISSED the 90% bar: 80% (8/10). U09 (Gemini Ultra, SuperGLUE) matched the generic dataset name 'accuracy'; U10 (Claude 2) matched an entity named 'claude' (vector 0.865). Both are name-match false links.
- [x] Relate path correctness on 20 entity pairs
      **Result:** 20/20 paths found, 20/20 right length (the expected paths came from the same graph, so this is a consistency check, not independent proof).
- [x] Router accuracy on the labeled questions (proposed bar: at least 85%)
      **Result:** rules only 92% (46/50), bar 85% met; the model step was not measured.
- [ ] Local query cost at most $0.03; p95 at most 8 s (10 queries, one at a time)
      **Result:** cost about $0.0035 per answer, met; p95 latency NOT measured (mean 5.2 s).
- [x] Total Phase 4 spend within the approved cap ($0.80)
      **Result:** about $0.28 of $0.80.

## Tests

- [x] Unit tests: sanitiser, linking, expansion query, PageRank, budget split, labels, citation
      check, refusal and clarify, path finding, router rules
      **Result:** 394 tests pass.
- [x] Negative tests: a question with a key or email is redacted; a question that tries to make
      the system write a query changes nothing; an unknown cited ID is flagged; an ambiguous
      entity asks; a thin context refuses; cost cap stops
      **Result:** covered in tests.
- [x] Model calls mocked in routine tests and labelled as mocks
      **Result:** yes, labelled.
- [ ] `ruff` and `pytest` pass; CI green
      **Result:** locally in Docker; CI NOT run yet.

## Docs and review

- [ ] WALKTHROUGH.md, README, STATUS.md, DECISIONS.md updated
- [ ] Owner reviewed the new question sets and spot-checked the citation sample
