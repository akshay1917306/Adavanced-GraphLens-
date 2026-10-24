# Phase 2: Extraction and graph

Source: blueprint v1.0 sections 1.3 (G3, G4, G5, part of G6), 2.4, 2.5, 4.3, 5.1.

## Goal

Turn the text units into a **knowledge graph** in Neo4j: entities (Paper, Author, Method,
Dataset, Task, Organization) and relations between them (for example `IMPROVES_ON`), where
every node and every edge points back to the text units that support it.

## Requirements covered

| ID | Requirement | Plan |
|---|---|---|
| G3 | Ontology-constrained extraction with gleaning and schema validation | Structured JSON output checked against `ontology/research_v1.yaml` |
| G4 | Resolve and merge duplicate entities, keep aliases | Name normalising, blocking, scoring, LLM adjudication for the gray zone |
| G5 | Store the graph with provenance | Neo4j nodes and edges with `source_unit_ids` and `evidence_unit_ids` |
| G6 (part) | Embed entities | Entity vectors in a Neo4j vector index (communities and reports come in Phase 3) |

NFRs: cost control (estimate, cap, cache), reproducibility (prompt, model and ontology
versions are recorded), reliability (resumable, idempotent).

## Not in this phase

Communities and reports (Phase 3), local and global search, router, relate mode, citation
support check (Phases 3 and 4), UI (Phase 5). `CITES` (needs reference parsing) goes to the
backlog.

## Decisions taken before the build

- **Option A (owner, 2026-10-24):** keep a front-matter text unit (title, authors,
  affiliations) per paper so `AUTHORED_BY` and `AFFILIATED_WITH` have evidence. Email lines
  are removed. See CR-0003.
- D5 (extraction model) and D6 (gleaning passes) are measured on a 5% sample before the full run.

## Build steps

1. CR-0003: front-matter unit, chunker version 3, re-ingest, re-embed, remap evaluation evidence.
2. Ontology to a strict JSON schema, extraction prompt v1, extraction cache.
3. Run records (`index_runs`, `run_stages`), cost cap, resume.
4. Dry run on 5% of units: measure cost, compare gleaning 0 and 2, check model quality.
5. Full extraction (after the owner approves the cost).
6. Entity resolution with stored decisions.
7. Neo4j load: versioned constraint and index scripts, nodes, edges, vector index.
8. Quality report with the gate checks.
9. Labeled sets: 30 text units and candidate pairs (AI draft, owner review).
10. Tests, docs, README, CI.

## Cost (assumption, to be replaced by the dry-run measurement)

About $1 to $3.5 for the 25 development papers. About $10 to $40 for 200 to 300 papers (later,
separate approval). No batch of paid calls runs without a shown estimate and the owner's yes.
