# Phase 2 acceptance checks

Mark an item only after it was run, and say where it was run. Targets come from the blueprint;
the phase exit is "measured", so a missed target is reported, not hidden.

## Build

- [x] Front-matter unit kept (CR-0003); re-ingest and re-embed done; evaluation evidence remapped
      (751 units, 25 front-matter units, none with an email or web address; collection
      `units_qa_v0_baseline_2`; `eval-verify` 0 problems; evaluation sets version 2 loaded;
      111 tests pass; run 2026-10-24 on the owner's machine)
- [x] Extraction output is schema-valid: at least 99% (3 retries per unit)
      (100%: 0 of 751 units failed; but the second check dropped 573 of 4,184 proposed relations,
      13.7%, mostly types the predicate does not allow; see `QUALITY.md`)
- [x] Every edge has at least one evidence unit; every node has `source_unit_ids` (100%)
      (2,695 of 2,695 edges and 1,848 of 1,848 nodes, and the ids exist in `text_units`;
      measured by `quality-report` on the real Neo4j graph)
- [x] Relation precision measured on 30 labeled text units (target 0.80)
      (**0.81** on 182 relations, 20 unsure excluded (0.72 to 0.83 if they all went one way);
      owner confirmed all labels 2026-10-24)
- [x] Entity resolution precision, recall and F1 measured on labeled pairs (target F1 0.85)
      (measured, **F1 0.79 is a miss**: precision 1.00, recall 0.65 (0.75 and 0.60 before the
      symbol loosening, D26); owner confirmed all labels 2026-10-24)
- [ ] Duplicate entities in a sample audit (target at most 5%); orphan entities (at most 10%)
      (orphans were **17.5%** (a miss), then 1.6% after D25 left 298 lonely single-mention
      entities out; both numbers are in `QUALITY.md`; automatic duplicate proxy 2.6%, the
      owner's audit is still to do)
- [ ] Second run makes zero model calls (cache) and the graph is unchanged
      (extraction part done: the repeated `idx2-full-g0` run took 750 units from the cache and
      called the model only for the one unit that had failed; the graph part waits for step 7)
- [x] The cost cap stops a run cleanly and it can resume
      (tested with a mock model against the real database: a capped run stopped, the next run
      took finished units from the cache and did only the rest)
- [x] Neo4j constraints and indexes come from versioned scripts; counts match the resolution
      output (scripts `V001` to `V003`, checksums stored in `SchemaVersion` nodes; real run
      2026-10-24: 1,848 entities and 2,695 relations in Neo4j, as resolved; all 1,848 embedded;
      vector index ONLINE; 0 entities without source units; 0 edges without evidence units;
      there is no entity table in Postgres, so the counts are compared with the resolution)
- [x] No model-written Cypher anywhere (templated, parameterised queries only; labels and
      relationship types come from the ontology and are checked first; tested with an injection
      string)
- [ ] Gleaning 0 versus 2 and the model choice measured on a 5% sample (D5, D6)
      (done for counts and cost on 43 units: +8% entities, +22% relations, +57% cost; **precision
      of the added items is not measured yet**, and the model comparison waits for labeled units)

## Tests

- [ ] Unit tests: schema validation, name normalising, resolution scoring, graph load idempotency
- [ ] Negative tests: unknown type or predicate rejected, edge without evidence rejected,
      instructions hidden in a text unit cannot add edges outside the schema, cost cap stops
- [ ] Model calls mocked in routine tests and labelled as mocks
- [ ] `ruff` and `pytest` pass; CI green

## Docs and review

- [ ] WALKTHROUGH.md, README, STATUS.md updated
- [ ] Owner reproduced the run steps and reviewed the labeled data
