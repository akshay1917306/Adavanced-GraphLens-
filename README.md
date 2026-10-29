# GraphLens (Advanced GraphRAG pipeline)

GraphLens turns a document collection into a knowledge graph and answers questions
by following the graph, showing the evidence for every answer. It is built from the
*Advanced GraphLens Pipeline Blueprint v1.0* (2026-10-17).

> **Status: Phase 1 (Baseline RAG and evaluation set v0) is done and tagged `phase-1`. Phase 2 (graph) is done and tagged `phase-2`. Phase 3 (communities and global search) is done and tagged `phase-3`. Phase 4 (local search, router, relate, citation check) is done and tagged `phase-4`. Phase 5 (API and one Ask screen) is done and tagged `phase-5`. Phase 6 (user data and hardening) is done and tagged `phase-6`.**
> The plain vector RAG works and is measured. A first knowledge graph exists in Neo4j (not yet
> used for answers, and its relation precision is 0.81 and entity-resolution F1 0.79, below the target). The Ask screen (Phase 5) shows saved answers only; live answers are not wired in. Development data: 25 open-licensed research papers.

## Status

| Phase | Status |
|---|---|
| 0. Setup and decisions | Approved, merged, tag `phase-0` |
| 1. Baseline RAG and evaluation set v0 | Approved, merged, tag `phase-1` |
| 2. Extraction and graph | Approved, merged, tag `phase-2` ([plan](docs/phases/phase-2-extraction/BRIEF.md), [walkthrough](docs/phases/phase-2-extraction/WALKTHROUGH.md)) |
| 3. Communities and global search | Approved, merged, tag `phase-3` ([plan](docs/phases/phase-3-communities/BRIEF.md), [walkthrough](docs/phases/phase-3-communities/WALKTHROUGH.md)) |
| 4. Local search, router, relate, citation check | Plan written, waiting for owner approval ([plan](docs/phases/phase-4-local-search/BRIEF.md)) |
| 5 to 8 | Planned, see [docs/phases](docs/phases/README.md) |

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
| Neo4j graph: 1,545 entities, 2,694 relations, with source and evidence passages, vector index | Implemented |
| Quality report on the graph | Implemented, see [QUALITY.md](docs/phases/phase-2-extraction/QUALITY.md) |
| Relation precision 0.81 (target 0.80) and entity-resolution F1 0.79 (target 0.85) | **Measured** on 182 relations and 110 pairs |
| 193 hierarchical communities, each with a cited report, embedded in Neo4j | Implemented |
| Global search (select, map, reduce) with progress and partial-failure handling | Implemented, command `global-ask` |
| Global win rate against the baseline: 100% on comprehensiveness and diversity (20 questions) | **Measured** with caveats (answers are 3.4 times longer; same-family judge; interval 84% to 100%) |
| Global search speed and cost: 8.4 s median and about half a cent per question | **Measured** (one query at a time) |
| Owner rating of communities and judge spot-check | Pending |
| Local search (entity linking, 2-hop expansion, PageRank, cited context), relate mode, router, citation check | Implemented, commands `local-ask`, `relate`, `ask-auto` |
| Local correctness on 30 hard multi-hop questions: 70% vs 53% for plain RAG (9 wins, 19 ties, 2 losses) | **Measured**: below the 75% target; intervals overlap (52-83% vs 36-70%) |
| Citation support 98% (122 of 124); refusal 8 of 10 (target 90% missed); relate 20 of 20 paths | **Measured**, see [Phase 4 STATUS](docs/phases/phase-4-local-search/STATUS.md) |
| Ask screen and API (`ask`, `feedback`, `examples`, read-only `status`) in replay mode | Implemented (tag `phase-5`); checked in the browser, see [Phase 5 STATUS](docs/phases/phase-5-ui/STATUS.md) |
| Live answers from the screen (search code inside the API) | Not built; package version conflict to settle first |
| Private history, saved answers, settings and delete-all for anonymous visitors (signed cookie) | Implemented (tag `phase-6`); two-profile check done, see [Phase 6 STATUS](docs/phases/phase-6-hardening/STATUS.md) |
| Rate limits, daily cost cap, security headers and CSP, audit log, request ids and log hygiene | Implemented (tag `phase-6`); 123 API tests pass |
| Dependency audit, secret scan, load test | **Measured**: web and API have no known advisories, pipeline has 2 accepted ones (D59), no secret in git history, no errors up to 10 concurrent requests |
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
docker compose up -d                                 # databases, API and web screen
docker compose run --rm pipeline index               # ingest and embed the 25 papers
docker compose run --rm pipeline ask "What makes ConditionalQA hard?"
```

If `data/corpus/qa_v0/pdfs/` is empty, first run
`python pipeline/corpus/build_manifest.py --count 25` and `python pipeline/corpus/download.py`.

| URL | What you see |
|---|---|
| http://localhost:8000/api/v1/health | JSON with `"status":"ok"` and four services |
| http://localhost:3000 | The Ask screen (saved example questions, answer, sources, evidence graph) |
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
docker compose run --rm --entrypoint pytest pipeline -q                  # 305 tests
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
- [Decision log](docs/DECISIONS.md) (D1 to D34), [ADRs and change requests](docs/adr/), [Backlog](docs/BACKLOG.md)
- [Baseline results](data/eval/v0/results/baseline-2026-10-23.md), [wireframes](docs/design/WIREFRAMES.md)

## Known limitations

- Only 25 development papers; the real corpus (200 to 300) is not loaded.
- The evaluation questions come from abstracts, so the local score (93%) is probably too easy.
  The judge is the same model as the answerer and was too strict in 2 of 4 spot-checks.
- Entity-resolution F1 is 0.79 against a 0.85 target: the resolver is strict, so many true duplicates stay separate. Claude drafted the labels and the owner confirmed them without changes.
- About 17.5% of extracted entities had no relation; lonely single-mention ones are left out of the graph.
- Citation checking only proves a cited number exists, not that the passage supports the claim.
- Text cleaning is heuristic (footnotes, equations and tables can be messy).
- Licenses come from the ACL Anthology policy page, not from each PDF.
- Not production-ready and not security-reviewed; do not expose it to the internet.

- Phase 4: local search reaches 70% correct on 30 hard questions (target 75%), better than plain RAG by about 17 points but not statistically separated; community reports add nothing to local answers; two unanswerable questions were answered because a generic word or a model name matched an entity; only 11 of 20 relate explanations passed the citation check; the baseline rerank was not built; p95 latency was not measured; the judge is the same model family.

- Phase 5: the screen replays 5 real saved answers and 2 refusals; any other question gets a refusal. Replayed answers show no cost or latency. Only local mode is replayed (no relate or global). There is no sign-in; one anonymous visitor owns all saved answers and ratings. No automated test proves script text stays text in the page (checked by hand in the browser).

- Phase 6: anonymous visitors only (no sign-in); a stolen cookie works until it expires or the data is deleted; no HTTPS, backups or monitoring; the cost cap and time limits were never exercised with a real model; retrieval does about 2 to 3 questions per second per process; `pypdf` and `pillow` have known advisories that are accepted for now; CI passed on the merge (all 6 jobs).

**Next planned phase:** Phase 7 (evaluate and launch: live answers with your OpenAI key, backups, HTTPS), not started; Phase 6 is approved, merged and tagged.
