# CR-0003: Keep a front-matter text unit for every paper

Status: **Approved by the owner on 2026-10-24** (option A)
Changes: Phase 1 cleaning (the "drop author lines before the abstract" rule) and chunker version.
Affects: Phase 2 (`AUTHORED_BY`, `AFFILIATED_WITH`) and everything that uses text unit IDs.

## Why

The ontology has `AUTHORED_BY` and `AFFILIATED_WITH`, and the blueprint says every edge must
have at least one evidence text unit. Phase 1 removed the title, author and affiliation lines
before the abstract, so no text unit could be evidence for those edges.

## Decision

- Keep the text before the abstract as a section named `Front matter` (title, authors,
  affiliations), which becomes the first text unit of the paper.
- Remove lines that contain an email address or a web address from it, so personal emails do not
  enter the database or reach the language model.
- `CHUNKER_VERSION` becomes `3`.
- Text unit IDs contain the ordinal, so every unit of a paper moves by one place (the old
  abstract unit `..._0000` becomes `..._0001`).

## Consequences

- The development corpus is ingested again from scratch (only the `qa_v0` rows are replaced).
- Embeddings are rebuilt into a new Qdrant collection `units_qa_v0_baseline_2` (free, local). The
  alias `units_live` moves to it. The old collection is deleted because it holds the same data
  under old IDs.
- Evaluation evidence is remapped by its exact quote (the quote must still be found in exactly one
  unit of the same paper) and loaded as **version 2** of the evaluation sets. Version 1 and the
  Phase 1 baseline results stay unchanged, as history.
- The Phase 1 baseline numbers were measured without front-matter units; they are not re-run
  (it would cost money) and are kept as recorded. A later run may differ slightly.
- Author names are personal data in a public paper. They are public information, but only
  synthetic or open-licensed documents are used in this project.

## Not decided here

`CITES` needs the reference list, which is still cut. It goes to the backlog.
