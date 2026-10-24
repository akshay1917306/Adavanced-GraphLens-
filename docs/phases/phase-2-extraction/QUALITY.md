# Quality report: idx2-full-g0

Measured by `quality-report` on the graph in Neo4j. Numbers only; no model was called.

| Check | Value | Target | Result |
|---|---|---|---|
| schema_validity | 100.0% | >= 99% | PASS |
| node_provenance | 100.0% | >= 100% | PASS |
| edge_evidence | 100.0% | >= 100% | PASS |
| ontology_conformance | 100.0% | >= 100% | PASS |
| embedding_coverage | 100.0% | >= 100% | PASS |
| duplicate_rate_proxy | 2.9% | <= 5% | PASS |
| orphan_rate | 17.5% | <= 10% | **MISS** |

## Not measured yet

- **relation_precision**: needs the 30 labeled text units (step 9); target 0.80
- **entity_resolution_f1**: needs the labeled candidate pairs (step 9); target 0.85
- **duplicate_rate_audit**: needs the owner's sample audit; the automatic number below is a proxy
- **communities**: Phase 3

## Details: schema_validity

```json
{
  "units": 751,
  "failed_units": 0,
  "relations_kept_by_the_second_check": 3611,
  "relations_dropped_by_the_second_check": 573,
  "dropped_by_reason": {
    "relation_end_not_in_entities": 196,
    "type_not_allowed_for_predicate": 377
  },
  "dropped_share": 0.137
}
```

## Details: node_provenance

```json
{
  "entities": 1848,
  "with_existing_source_units": 1848
}
```

## Details: edge_evidence

```json
{
  "edges": 2695,
  "with_existing_evidence_units": 2695
}
```

## Details: ontology_conformance

```json
{
  "edges": 2695,
  "allowed_by_ontology": 2695
}
```

## Details: embedding_coverage

```json
{
  "entities": 1848
}
```

## Details: duplicate_rate_proxy

```json
{
  "kind": "automatic proxy, not the owner's audit",
  "pairs": 28,
  "entities_involved": 54,
  "examples": [
    [
      "ComplexWebQuestions (CWQ)",
      "CWQ"
    ],
    [
      "OLTQA benchmark",
      "OLTQA dataset"
    ],
    [
      "w/ head",
      "w/o head"
    ],
    [
      "+K1\u2192Y",
      "K1"
    ],
    [
      "+K2\u2192Y",
      "K2"
    ],
    [
      "adaptation tuning",
      "adaptation tuning strategy"
    ],
    [
      "ANCE",
      "D ANCE+"
    ],
    [
      "augmentation in the hidden space",
      "hidden space augmentation"
    ],
    [
      "counterfactual reasoning approach",
      "counterfactual reasoning method"
    ],
    [
      "dense embedding based passage retrieval (DPR) models",
      "DPR"
    ],
    [
      "ETC",
      "ETC pipeline"
    ],
    [
      "FiD GAR+",
      "GAR+ & FiD"
    ],
    [
      "Greedy",
      "Greedy algorithm"
    ],
    [
      "language model architecture",
      "language models"
    ],
    [
      "LLMs",
      "pipeline of LLMs"
    ]
  ]
}
```

## Details: orphan_rate

```json
{
  "isolated": 323,
  "entities": 1848,
  "by_type": {
    "Author": 9,
    "Dataset": 57,
    "Method": 69,
    "Organization": 21,
    "Paper": 76,
    "Task": 91
  },
  "single_mention": 298
}
```
