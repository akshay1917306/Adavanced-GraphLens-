# GraphLens (Advanced GraphRAG pipeline)

GraphLens turns a document collection into a knowledge graph and answers questions
by following the graph, showing the evidence for every answer. It is built from the
*Advanced GraphLens Pipeline Blueprint v1.0* (2026-10-17).

> **Status: Phase 0 (Setup and decisions) built, waiting for owner review.**
> Nothing answers questions yet. All data in the repository is synthetic.

## Status

| Phase | Status |
|---|---|
| 0. Setup and decisions | Built, in review |
| 1. Baseline RAG and evaluation set | Planned (next) |
| 2 to 8 | Planned, see [docs/phases](docs/phases/README.md) |

## What works today

| Feature | State |
|---|---|
| Local stack: Postgres, Neo4j, Qdrant, Redis, API (Docker Compose) | Implemented |
| `GET /api/v1/health` (per-service status, 503 if one is down) | Implemented |
| Full Postgres schema from the blueprint (Alembic migration 0001) | Implemented |
| Ontology file and validator | Implemented |
| 10-document synthetic fixture corpus and loader | Implemented |
| Web placeholder showing service status | Implemented (placeholder) |
| CI: lint, tests, build | Written, not yet run on GitHub |
| Ingestion, search, graph, answers, UI | Planned |
| LLM calls (OpenAI, see [ADR-0001](docs/adr/ADR-0001-llm-provider-openai.md)) | Planned for Phase 1 |

## Prerequisites

Windows 11 with WSL2 (Ubuntu 24.04) or macOS, 16 GB RAM, Docker Desktop, Git, uv,
Node.js 22, VS Code. Details: [Phase 0 prerequisites](docs/phases/phase-0-setup/PREREQUISITES.md).

## Setup and run

Run these in the Ubuntu (WSL) terminal.

```bash
# Terminal 1, in the repository folder
cp .env.example .env            # then replace the placeholder passwords
docker compose up -d --build
cd api && uv sync && uv run python -m app.fixtures --load

# Terminal 2, in web/
npm ci && npm run dev
```

| URL | What you see |
|---|---|
| http://localhost:8000/api/v1/health | JSON with `"status":"ok"` and four services |
| http://localhost:8000/docs | API documentation |
| http://localhost:3000 | Placeholder page listing service status |
| http://localhost:7474 | Neo4j Browser (user `neo4j`, password from `.env`) |
| http://localhost:6333/dashboard | Qdrant dashboard |

Stop: `Ctrl+C` in terminal 2, then `docker compose down` in the repository folder.

Full steps, expected results, and common errors: [Phase 0 walkthrough](docs/phases/phase-0-setup/WALKTHROUGH.md).

## Environment variables

Names only; real values live in your git-ignored `.env`. See `.env.example`.

`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`,
`NEO4J_PASSWORD`, `NEO4J_HTTP_PORT`, `NEO4J_BOLT_PORT`, `QDRANT_PORT`, `REDIS_PORT`,
`API_PORT`, `OPENAI_API_KEY` (Phase 1+), `LLM_MODEL_SMALL`, `LLM_MODEL_MAIN`,
`LLM_DAILY_COST_CAP_USD`.

Never commit `.env` or paste keys into chats, issues, or screenshots.

## Tests

```bash
cd api && uv run ruff check . && uv run pytest
cd web && npm run lint && npm run build
```

Database tests run only when `DATABASE_URL` points at a throwaway database; see the walkthrough.

## Documentation

- [Phases](docs/phases/README.md) and [Phase 0 docs](docs/phases/phase-0-setup/)
- [Decision log](docs/DECISIONS.md), [ADRs](docs/adr/), [Backlog](docs/BACKLOG.md)
- [Wireframes](docs/design/WIREFRAMES.md)

## Known limitations

- Phase 0 only: no ingestion, search, or answers.
- Fixture corpus is synthetic; the real corpus topic is still to be chosen.
- CI has not run on GitHub yet.

**Next planned phase:** Phase 1, Baseline RAG and evaluation set v0.
