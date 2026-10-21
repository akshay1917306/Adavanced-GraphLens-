# Fixture corpus `research_v0`

Ten **synthetic** research "papers" written for GraphLens tests. Every name, method,
dataset, organization, and number in them is fictional. They are not real papers.

Why synthetic: the owner's rule is synthetic data only during development, and we
know the true facts, so tests in later phases can compare the extracted graph with
a known answer (`expected_relations.csv`).

| File | Purpose |
|---|---|
| `docs/` | The 10 documents (Markdown, plain text, HTML) |
| `MANIFEST.csv` | One row per document: title, format, license, trust level, SHA-256 hash |
| `expected_relations.csv` | Draft ground-truth relations for extraction tests (Phase 2) |

`p10_untrusted_note.md` contains a deliberate prompt-injection attempt and has
trust level `low`. Later phases must **not** turn its fake claims into graph edges.

A PDF fixture is added in Phase 1 together with the PDF parser.

If you edit a document, its hash changes. Re-run
`uv run python -m app.fixtures --check` from `api/` and update `MANIFEST.csv`.
