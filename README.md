# GraphLens (Advanced GraphRAG pipeline)

GraphLens turns a document collection into a knowledge graph and answers questions
by following the graph, showing the evidence for every answer. It is built from the
*Advanced GraphLens Pipeline Blueprint v1.0* (2026-10-17).

> **Status: Phase 1 (Baseline RAG and evaluation set v0) built, waiting for owner review.**
> The plain vector RAG works and is measured. There is **no graph yet** (Phase 2) and no
> web interface for questions (Phase 5). Development data: 25 open-licensed research papers.

## Status

| Phase | Status |
|---|---|
| 0. Setup and decisions | Approved, merged, tag `phase-0` |
| 1. Baseline RAG and evaluation set v0 | Built, in review (not pushed yet) |
| 2. Extraction and graph | Planned (next) |
| 3 to 8 | Planned, see [docs/phases](docs/phases/README.md) |

## What works today

| Feature | State |
|---|---|
| Local stack: Postgres, Neo4j, Qdrant, Redis, API (Docker Compose) | Implemented |
| `GET /api/v1/health` | Implemented |
| Postgres schema (blueprint, 23 tables) | Implemented |
| Corpus of 25 QA papers with license manifest and download script | Implemented |
| PDF reading, cleaning, section detection, chunking (450 tokens, 75 overlap) | Implemented |
| Ingest into Postgres (726 text units), safe to repeat | Implemented |
| Local embeddings (dense and sparse) into Qdrant | Implemented |
| Baseline answer with citation-number check and refusal (OpenAI `gpt-4.1-mini`) | Implemented |
| Evaluation set v0 (30 local, 10 global) and runner with cost cap | Implemented |
| Prefect flow: ingest then embed, with retries | Implemented |
| Baseline results: 93% correct on local, 0% on global questions | **Measured** (LLM judge, see limits) |
| Graph, communities, global search, router, relate, citation support check | Planned (Phases 2 to 4) |
| Question-answering web UI | Planned (Phase 5); simpler design proposed in [CR-0001](docs/adr/CR-0001-simplified-dashboard.md) |
| CI for the `pipeline/` folder | Written, **not yet run on GitHub** |

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
| http://localhost:6333/dashboard | Qdrant dashboard (collection `units_qa_v0_baseline_1`, 726 points) |
| http://localhost:7474 | Neo4j Browser (empty until Phase 2) |

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
docker compose run --rm --entrypoint pytest pipeline -q                  # 106 tests
docker compose run --rm --no-deps --entrypoint ruff pipeline check .
docker compose run --rm pipeline eval-verify                             # evidence quotes exist
```

The earlier API and web checks are in the [Phase 0 walkthrough](docs/phases/phase-0-setup/WALKTHROUGH.md).
Tests that would call OpenAI use labelled mocks. Integration tests use their own temporary
database and Qdrant collections.

## Documentation

- [Phases](docs/phases/README.md): [Phase 0](docs/phases/phase-0-setup/) and
  [Phase 1](docs/phases/phase-1-baseline/) ([walkthrough](docs/phases/phase-1-baseline/WALKTHROUGH.md))
- [Decision log](docs/DECISIONS.md) (D1 to D21), [ADRs and change requests](docs/adr/), [Backlog](docs/BACKLOG.md)
- [Baseline results](data/eval/v0/results/baseline-2026-10-23.md), [wireframes](docs/design/WIREFRAMES.md)

## Known limitations

- Only 25 development papers; the real corpus (200 to 300) is not loaded.
- The evaluation questions come from abstracts, so the local score (93%) is probably too easy.
  The judge is the same model as the answerer and was too strict in 2 of 4 spot-checks.
- Citation checking only proves a cited number exists, not that the passage supports the claim.
- Text cleaning is heuristic (footnotes, equations and tables can be messy).
- Licenses come from the ACL Anthology policy page, not from each PDF.
- Not production-ready and not security-reviewed; do not expose it to the internet.

**Next planned phase:** Phase 2, Extraction and graph.
