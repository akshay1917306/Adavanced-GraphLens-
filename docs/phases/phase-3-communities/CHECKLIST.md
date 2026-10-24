# Phase 3 acceptance checks

Mark an item only after it was run, and say where it was run. Targets come from the blueprint;
the exit is "measured", so a missed target is reported, not hidden.

## Build

- [x] Leiden library installs in the image and runs on the real graph (D28: `graspologic-native`
      1.3.1; run 2026-10-24 on the owner's machine)
- [x] Hierarchical communities: same seed gives the same result; every entity is in a community
      at every level (100%); `CHILD_OF` links form a tree (193 communities; `community_assignment`
      100%; a second write gives the same graph)
- [x] Every community has a report (100%); communities under 3 entities have a flagged stub (D29)
      (193 of 193; 55 stubs)
- [x] Every finding in a model-written report cites text units that exist and belong to that
      community's evidence (100%) (`report_citations_valid` 100% on the stored reports; the
      'belongs to the evidence' part is enforced when the report is written)
- [x] Reports are embedded and findable through a Neo4j vector index (`report_embedding_coverage`
      100%)
- [x] Dry-run estimate shown before the paid run; the cost cap stops a run cleanly (estimate
      $0.25, actual $0.2224; the cap stop is tested with a mock model)
- [x] Second run makes zero model calls (cache by input hash); changing one community's input
      regenerates only that report (tested with a mock model against the real database; on
      the real data the repeated `global-eval` run made no model call)
- [x] Global search: dynamic selection (at most 40 reports), parallel map batches, reduce,
      progress event per batch, a failed batch gives a partial answer that says so (tests, and
      a real failed batch was seen and reported as partial)
- [x] Report text is treated as data in prompts; an instruction hidden in a report changes
      nothing (tested that angle brackets cannot close the tags; how a real model reacts to a
      hidden instruction was **not** tested)
- [x] No model-written Cypher anywhere (templated, parameterised queries only)

## Measured

- [x] Global win rate against the baseline: at least 60% on comprehensiveness and on diversity
      (answer order swapped; report the number of questions and the confidence honestly)
      (**100% and 100% on 20 questions, interval 84% to 100%**; answers are 3.4 times longer
      and the judge is the same model family; directness 45%)
- [ ] Ablation: global search with and without dynamic selection (cost, latency, win rate)
      (win rate measured: 10 of 10 without selection, same as with; **cost and latency not
      measured yet**, `global-bench` waits for the owner's yes)
- [ ] Owner rating of 20 sampled communities, coherence 1 to 5 (proposed bar: average at least 3.5)
- [ ] Owner spot-check of 10 judge verdicts
- [ ] Global query cost at most $0.15 and p95 latency at most 30 s with progress (10 queries)
      (one real query: 11.5 s and $0.006; the 10-query benchmark is not run yet)
- [x] Total Phase 3 spend within the approved cap (about $0.53 of $2.00)

## Tests

- [x] Unit tests: graph export, Leiden determinism, report input builder, hash cache, stub rule,
      citation validation, selection, batching, reduce, partial failure, pairwise scoring
- [x] Negative tests: report citing a unit outside its evidence is rejected, injected instruction
      ignored, cost cap stops, empty selection gives a clear message
- [x] Model calls mocked in routine tests and labelled as mocks
- [ ] `ruff` and `pytest` pass; CI green (305 tests pass and `ruff` is clean locally; CI has
      not run)

## Docs and review

- [x] WALKTHROUGH.md, README, STATUS.md, DECISIONS.md updated
- [ ] Owner reproduced the run steps and reviewed the community and judge samples
