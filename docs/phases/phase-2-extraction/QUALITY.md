# Quality report: idx2-full-g0

Measured by `quality-report` on the graph in Neo4j. Numbers only; no model was called.

| Check | Value | Target | Result |
|---|---|---|---|
| schema_validity | 100.0% | >= 99% | PASS |
| node_provenance | 100.0% | >= 100% | PASS |
| edge_evidence | 100.0% | >= 100% | PASS |
| ontology_conformance | 100.0% | >= 100% | PASS |
| embedding_coverage | 100.0% | >= 100% | PASS |
| duplicate_rate_proxy | 2.6% | <= 5% | PASS |
| orphan_rate | 1.6% | <= 10% | PASS |
| orphan_rate_before_pruning | 17.5% | <= 10% | **MISS** |

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
  "entities": 1550,
  "with_existing_source_units": 1550
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
  "entities": 1550
}
```

## Details: duplicate_rate_proxy

```json
{
  "kind": "automatic proxy, not the owner's audit",
  "pairs": 21,
  "entities_involved": 41,
  "examples": [
    [
      "ComplexWebQuestions (CWQ)",
      "CWQ"
    ],
    [
      "w/ head",
      "w/o head"
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
      "LLMs",
      "pipeline of LLMs"
    ],
    [
      "neural models",
      "neural module networks"
    ],
    [
      "oracle strategy",
      "oracle \u03c0*"
    ],
    [
      "our method",
      "Ours"
    ],
    [
      "parametric models",
      "Pm"
    ]
  ]
}
```

## Details: orphan_rate

```json
{
  "isolated": 25,
  "entities": 1550,
  "by_type": {
    "Dataset": 6,
    "Method": 1,
    "Organization": 1,
    "Paper": 8,
    "Task": 9
  },
  "single_mention": 0
}
```

## Details: orphan_rate_before_pruning

```json
{
  "by_type": {
    "Task": 91,
    "Paper": 76,
    "Author": 9,
    "Method": 69,
    "Dataset": 57,
    "Organization": 21
  },
  "entities": 1848,
  "isolated": 323,
  "examples_left_out": [
    "Author: Aaron Chan",
    "Author: Allen",
    "Author: authors of this paper",
    "Author: crowd annotators",
    "Author: Dong-Ho Lee",
    "Author: experts",
    "Author: Qihan Liu",
    "Author: WEBGPT annotators",
    "Author: Woojeong Jin",
    "Dataset: AI Research Assistant",
    "Dataset: AQUAINT corpus",
    "Dataset: ARC",
    "Dataset: Aseen",
    "Dataset: ASQA LFQA dataset",
    "Dataset: background KG",
    "Dataset: Citation Graph Explorer",
    "Dataset: Complex WebQuestions 1.1 (CWQ)",
    "Dataset: CronQuestion",
    "Dataset: distractor setting",
    "Dataset: E2E",
    "Dataset: enterprise documents",
    "Dataset: Entire Data (3.6K)",
    "Dataset: expert evaluation of long-form answers",
    "Dataset: fact corpus C",
    "Dataset: FinTabNet",
    "Dataset: GenWiki",
    "Dataset: Google-RE",
    "Dataset: Head@3",
    "Dataset: Human",
    "Dataset: John_Lennon"
  ],
  "left_out_of_the_graph": 298
}
```
