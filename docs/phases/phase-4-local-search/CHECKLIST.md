# Phase 4 acceptance checks

Mark an item only after it was run, and say where it was run. Targets come from the blueprint;
the exit is "measured", so a missed target is reported, not hidden.

## Build

- [ ] Sanitiser: at most 4,000 characters; keys, tokens and emails are redacted before anything
      is logged or sent
- [ ] Entity linking finds the right seed entities for the benchmark questions (measured; report
      the share where the expected entity is among the 5 seeds)
- [ ] Expansion uses one fixed, parameterised Cypher template; at most 200 candidates; no
      model-written Cypher anywhere
- [ ] Personalized PageRank in numpy is deterministic and keeps the top 60 nodes
- [ ] Context respects the 8,000-token budget and its split; every item carries a `[T]`, `[E]`
      or `[C]` label
- [ ] Citation check: every cited ID exists in the context (100% of benchmark answers or the
      failures are listed); sentences naming entities that are not in the context are flagged;
      the result is `verified`, `warning` or `not_checked`
- [ ] Refuse when no seed is similar enough or the evidence is thin; ask when an entity is
      ambiguous
- [ ] Relate mode: up to 3 paths of at most 4 hops, evidence for every hop, nearest shared
      communities when there is no path
- [ ] Router: rules plus a model call; confidence under 0.6 runs local and says so; the mode can
      be forced
- [ ] Baseline mode gets the optional rerank (top 20 to 5)
- [ ] Dry-run estimate shown before each paid batch; the cost cap stops a run cleanly

## Measured

- [ ] Local correctness on the hard multi-hop set: at least 75%, and at least 15 points above the
      baseline (report the number of questions and the interval)
- [ ] Local correctness on the easy set (ceiling 100%, baseline was 93%)
- [ ] Ablations: baseline, plus entity linking, plus expansion, plus PageRank, plus community
      reports (correctness, cost, latency)
- [ ] Citation precision (a cited passage supports its claim): at least 90% by the judge, and the
      owner's spot-check of 10 answers
- [ ] Refusal accuracy on 10 unanswerable questions: at least 90%
- [ ] Relate path correctness on 20 entity pairs
- [ ] Router accuracy on the labeled questions (proposed bar: at least 85%)
- [ ] Local query cost at most $0.03; p95 at most 8 s (10 queries, one at a time)
- [ ] Total Phase 4 spend within the approved cap

## Tests

- [ ] Unit tests: sanitiser, linking, expansion query, PageRank, budget split, labels, citation
      check, refusal and clarify, path finding, router rules
- [ ] Negative tests: a question with a key or email is redacted; a question that tries to make
      the system write a query changes nothing; an unknown cited ID is flagged; an ambiguous
      entity asks; a thin context refuses; cost cap stops
- [ ] Model calls mocked in routine tests and labelled as mocks
- [ ] `ruff` and `pytest` pass; CI green

## Docs and review

- [ ] WALKTHROUGH.md, README, STATUS.md, DECISIONS.md updated
- [ ] Owner reviewed the new question sets and spot-checked the citation sample
