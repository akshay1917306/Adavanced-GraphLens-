# Phase 3 acceptance checks

Mark an item only after it was run, and say where it was run. Targets come from the blueprint;
the exit is "measured", so a missed target is reported, not hidden.

## Build

- [ ] Leiden library installs in the image and runs on the real graph (D28)
- [ ] Hierarchical communities: same seed gives the same result; every entity is in a community
      at every level (100%); `CHILD_OF` links form a tree
- [ ] Every community has a report (100%); communities under 3 entities have a flagged stub (D29)
- [ ] Every finding in a model-written report cites text units that exist and belong to that
      community's evidence (100%)
- [ ] Reports are embedded and findable through a Neo4j vector index
- [ ] Dry-run estimate shown before the paid run; the cost cap stops a run cleanly
- [ ] Second run makes zero model calls (cache by input hash); changing one community's input
      regenerates only that report
- [ ] Global search: dynamic selection (at most 40 reports), parallel map batches, reduce,
      progress event per batch, a failed batch gives a partial answer that says so
- [ ] Report text is treated as data in prompts; an instruction hidden in a report changes nothing
- [ ] No model-written Cypher anywhere (templated, parameterised queries only)

## Measured

- [ ] Global win rate against the baseline: at least 60% on comprehensiveness and on diversity
      (answer order swapped; report the number of questions and the confidence honestly)
- [ ] Ablation: global search with and without dynamic selection (cost, latency, win rate)
- [ ] Owner rating of 20 sampled communities, coherence 1 to 5 (proposed bar: average at least 3.5)
- [ ] Owner spot-check of 10 judge verdicts
- [ ] Global query cost at most $0.15 and p95 latency at most 30 s with progress (10 queries)
- [ ] Total Phase 3 spend within the approved cap

## Tests

- [ ] Unit tests: graph export, Leiden determinism, report input builder, hash cache, stub rule,
      citation validation, selection, batching, reduce, partial failure, pairwise scoring
- [ ] Negative tests: report citing a unit outside its evidence is rejected, injected instruction
      ignored, cost cap stops, empty selection gives a clear message
- [ ] Model calls mocked in routine tests and labelled as mocks
- [ ] `ruff` and `pytest` pass; CI green

## Docs and review

- [ ] WALKTHROUGH.md, README, STATUS.md, DECISIONS.md updated
- [ ] Owner reproduced the run steps and reviewed the community and judge samples
