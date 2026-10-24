# GraphLens (Advanced GraphRAG pipeline)

GraphLens turns a document collection into a knowledge graph and answers questions
by following the graph, showing the evidence for every answer. It is built from the
*Advanced GraphLens Pipeline Blueprint v1.0* (2026-10-17).

> **Status: Phase 1 (Baseline RAG and evaluation set v0) is done and tagged `phase-1`. Phase 2 (graph) is built on a branch and waits for the owner's review.**
> The plain vector RAG works and is measured. A first knowledge graph exists in Neo4j (not yet
> used for answers, and its accuracy numbers are drafts). There is no web interface for
> questions (Phase 5). Development data: 25 open-licensed research papers.

## Status

| Phase | Status |
|---|---|
| 0. Setup and decisions | Approved, merged, tag `phase-0` |
| 1. Baseline RAG and evaluation set v0 | Approved, merged, tag `phase-1` |
| 2. Extraction and graph | Built on branch `phase-2/extraction`, **not approved or pushed** ([plan](docs/phases/phase-2-extraction/BRIEF.md), [walkthrough](docs/phases/phase-2-extraction/WALKTHROUGH.md)) |
| 3 to 8 | Planned, see [docs/phases](docs/phases/README.md) |

## What works today

| Feature | State |
|---|---|
| Local stack: Postgres, Neo4j, Qdrant, Redis, API (Docker Compose) | Implemented |
| `GET /api/v1/health` | Implemented |
| Postgres schema (blueprint, 23 tables) | Implemented |
| Corpus of 25 QA papers with license manifest and download script | Implemented |
| PDF reading, cleaning, section detection, chunking (450 tokens, 75 overlap) | Implemented |
| Ingest into Postgres (751 text units, including one front-matter unit per paper), safe to repeat | Implemented |
| Local embeddings (dense and sparse) into Qdrant | Implemented |
| Baseline answer with citation-number check and refusal (OpenAI `gpt-4.1-mini`) | Implemented |
| Evaluation set v0 (30 local, 10 global) and runner with cost cap | Implemented |
| Prefect flow: ingest then embed, with retries | Implemented |
| Baseline results: 93% correct on local, 0% on global questions | **Measured** (LLM judge, see limits) |
| Ontology-based extraction of entities and relations (751 units, cached, cost-capped) | Implemented |
| Entity resolution with stored decisions and a merge guard | Implemented |
| Neo4j graph: 1,550 entities, 2,695 relations, with source and evidence passages, vector index | Implemented |
| Quality report on the graph | Implemented, see [QUALITY.md](docs/phases/phase-2-extraction/QUALITY.md) |
| Relation precision 0.81 and entity-resolution F1 0.75 | **Draft** (labels not owner-reviewed yet) |
| Communities, global search, router, relate, citation support check | Planned (Phases 3 and 4) |
| Question-answering web UI | Planned (Phase 5); simpler design proposed in [CR-0001](docs/adr/CR-0001-simplified-dashboard.md) |
| CI for the `pipeline/` folder | Implemented (all 4 jobs passed on GitHub for Phase 1) |

## Prerequisites

- Windows 11 or macOS, 16 GB RAM, about 10 GB free disk.
- **Docker Desktop** (CPU virtualization turned on in BIOS). That is all you need to run
  everything; Ubuntu/WSL, uv and Node are optional.
- Python 3.11 or newer only if you want to run the two corpus scripts yourself.
- An **OpenAI API key** and a spending limit set in your OpenAI dashboard (the baseline costs
  about $0.001 per question and about $0.05 for the 40-question evaluation).

## Setup and run

Run in PowerShell (or any shell) inside the repository folder. Create `.env` first: copy
`.env.example`, then put your own passwords and `OPENAI_API_KEY` in it. Never commit `.env`.

```bash
docker compose up -d                                 # databases and API
docker compose run --rm pipeline index               # ingest and embed the 25 papers
docker compose run --rm pipeline ask "What makes ConditionalQA hard?"
```

If `data/corpus/qa_v0/pdfs/` is empty, first run
`python pipeline/corpus/build_manifest.py --count 25` and `python pipeline/corpus/download.py`.

| URL | What you see |
|---|---|
| http://localhost:8000/api/v1/health | JSON with `"status":"ok"` and four services |
| http://localhost:8000/docs | API documentation |
| http://localhost:6333/dashboard | Qdrant dashboard (collection `units_qa_v0_baseline_2`, 751 points; other collections there, such as `dinosaurs`, are Qdrant sample data) |
| http://localhost:7474 | Neo4j Browser (sign in as `neo4j` with `NEO4J_PASSWORD`; the graph is there once `graph-load` has run) |

Evaluation: `docker compose run --rm pipeline eval-run --dry-run` shows the cost first; the real
run is in the [Phase 1 walkthrough](docs/phases/phase-1-baseline/WALKTHROUGH.md).

Stop: `docker compose down` (keeps data) or `docker compose down -v` (deletes data too).

## Environment variables

Names only; real values live in your git-ignored `.env`. See `.env.example`.

`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`, `NEO4J_PASSWORD`,
`NEO4J_HTTP_PORT`, `NEO4J_BOLT_PORT`, `QDRANT_PORT`, `REDIS_PORT`, `API_PORT`,
`OPENAI_API_KEY`, `LLM_MODEL_SMALL`, `LLM_MODEL_MAIN`, `LLM_DAILY_COST_CAP_USD`
(the daily cap is **not enforced by any code yet**; use the dashboard limit and `--max-cost-usd`).

## Tests

```bash
docker compose up -d postgres qdrant
docker compose run --rm --entrypoint pytest pipeline -q                  # 242 tests
docker compose run --rm --no-deps --entrypoint ruff pipeline check .
docker compose run --rm pipeline eval-verify                             # evidence quotes exist
```

The earlier API and web checks are in the [Phase 0 walkthrough](docs/phases/phase-0-setup/WALKTHROUGH.md).
Tests that would call OpenAI use labelled mocks. Integration tests use their own temporary
database and Qdrant collections.

## Documentation

- [Phases](docs/phases/README.md): [Phase 0](docs/phases/phase-0-setup/),
  [Phase 1](docs/phases/phase-1-baseline/) ([walkthrough](docs/phases/phase-1-baseline/WALKTHROUGH.md)) and
  [Phase 2](docs/phases/phase-2-extraction/) ([walkthrough](docs/phases/phase-2-extraction/WALKTHROUGH.md))
- [Decision log](docs/DECISIONS.md) (D1 to D25), [ADRs and change requests](docs/adr/), [Backlog](docs/BACKLOG.md)
- [Baseline results](data/eval/v0/results/baseline-2026-10-23.md), [wireframes](docs/design/WIREFRAMES.md)

## Known limitations

- Only 25 development papers; the real corpus (200 to 300) is not loaded.
- The evaluation questions come from abstracts, so the local score (93%) is probably too easy.
  The judge is the same model as the answerer and was too strict in 2 of 4 spot-checks.
- The graph's accuracy numbers (relation precision, entity-resolution F1) are drafts until the owner reviews the labels; the resolver is strict, so many true duplicates stay separate.
- About 17.5% of extracted entities had no relation; lonely single-mention ones are left out of the graph.
- Citation checking only proves a cited number exists, not that the passage supports the claim.
- Text cleaning is heuristic (footnotes, equations and tables can be messy).
- Licenses come from the ACL Anthology policy page, not from each PDF.
- Not production-ready and not security-reviewed; do not expose it to the internet.

**Next planned phase:** owner review and approval of Phase 2, then Phase 3 (communities and global search).
