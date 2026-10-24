# Phase 2 acceptance checks

Mark an item only after it was run, and say where it was run. Targets come from the blueprint;
the phase exit is "measured", so a missed target is reported, not hidden.

## Build

- [x] Front-matter unit kept (CR-0003); re-ingest and re-embed done; evaluation evidence remapped
      (751 units, 25 front-matter units, none with an email or web address; collection
      `units_qa_v0_baseline_2`; `eval-verify` 0 problems; evaluation sets version 2 loaded;
      111 tests pass; run 2026-10-24 on the owner's machine)
- [ ] Extraction output is schema-valid: at least 99% (3 retries per unit)
- [ ] Every edge has at least one evidence unit; every node has `source_unit_ids` (100%)
- [ ] Relation precision measured on 30 labeled text units (target 0.80)
- [ ] Entity resolution precision, recall and F1 measured on labeled pairs (target F1 0.85)
- [ ] Duplicate entities in a sample audit (target at most 5%); orphan entities (at most 10%)
- [ ] Second run makes zero model calls (cache) and the graph is unchanged
- [ ] The cost cap stops a run cleanly and it can resume
- [ ] Neo4j constraints and indexes come from versioned scripts; counts match Postgres
- [ ] No model-written Cypher anywhere (templated, parameterised queries only)
- [ ] Gleaning 0 versus 2 and the model choice measured on a 5% sample (D5, D6)

## Tests

- [ ] Unit tests: schema validation, name normalising, resolution scoring, graph load idempotency
- [ ] Negative tests: unknown type or predicate rejected, edge without evidence rejected,
      instructions hidden in a text unit cannot add edges outside the schema, cost cap stops
- [ ] Model calls mocked in routine tests and labelled as mocks
- [ ] `ruff` and `pytest` pass; CI green

## Docs and review

- [ ] WALKTHROUGH.md, README, STATUS.md updated
- [ ] Owner reproduced the run steps and reviewed the labeled data
