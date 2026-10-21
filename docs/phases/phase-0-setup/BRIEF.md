# Phase 0 Brief: Setup and decisions

Status: **Approved by owner on 2026-10-21; built; waiting for owner review.** See STATUS.md.

Source: Advanced GraphLens Pipeline Blueprint v1.0 (2026-10-17), section 5.1 row "0. Setup and decisions", plus ADR-0001 (OpenAI as LLM provider).

## 1. Goal

Get a working, empty project skeleton that boots on the owner's machine, and close the open decisions in blueprint section 5.3, so Phase 1 (Baseline RAG) can start without surprises.

Blueprint exit criteria for this phase:
- Decisions in section 5.3 are closed (decided, or explicitly assigned to the phase that measures them).
- The local stack boots (Neo4j, Qdrant, Postgres, Redis).
- A small fixture corpus loads.

## 2. Requirements covered

Phase 0 does not deliver a user-facing feature (no G1 to G31 requirement is completed here). It lays groundwork for:

| Requirement | What Phase 0 does for it |
|---|---|
| G1, G2 (ingest, chunk) | Fixture corpus of 10 licensed documents in the repo; real ingestion is Phase 1 |
| G20 (run management, cost cap) | Config placeholders for cost cap and model tiers, no LLM calls yet |
| NFR Reproducibility | Pinned dependency versions, `.env.example`, versioned ontology file |
| NFR Privacy | Corpus licence check recorded per document; secrets only in ignored `.env` |
| NFR Reliability | Health checks for every container |
| 2.11 CI/CD | GitHub Actions skeleton: lint and unit tests |

## 3. What we will build

1. **Repository structure**: `api/` (Python 3.11, FastAPI), `web/` (Next.js, TypeScript, placeholder page), `ontology/`, `data/fixtures/`, `docs/`. (`pipeline/` is created in Phase 1 with the first real flow, so we do not commit an empty folder.)
2. **Docker Compose** with Neo4j 5 Community, Qdrant, Postgres 16, Redis, plus the API with a `/api/v1/health` endpoint that reports which services are reachable.
3. **Config**: `.env.example` with fake placeholders only (`OPENAI_API_KEY=sk-placeholder`, `LLM_MODEL_SMALL`, `LLM_MODEL_MAIN`, database passwords). Real `.env` is git-ignored.
4. **Ontology draft** `ontology/research_v1.yaml`: 6 entity types and 8 predicates from blueprint 2.4.
5. **Fixture corpus**: 10 **synthetic** research papers (changed during build: arXiv was not reachable from the build environment, and the owner's rule is synthetic data during development), plus `data/fixtures/research_v0/MANIFEST.csv` with licence, trust level, and hash. A loader checks the files and registers them in Postgres.
6. **First Alembic migration**: all Postgres tables from blueprint 4.4 (the blueprint says all tables are created in the first migration).
7. **CI skeleton**: GitHub Actions running ruff, eslint, and pytest.
8. **Decision log**: `docs/DECISIONS.md` closing each 5.3 item.
9. **Low-fidelity wireframes** (simple sketches in `docs/design/`) for Ask, evidence graph, Explore, admin run detail.
10. **Phase docs**: BRIEF, PREREQUISITES, CHECKLIST, PROMPT, STATUS, WALKTHROUGH for Phase 0, `docs/adr/ADR-0001`, and an updated root README.

## 4. Excluded from Phase 0

- Any LLM call (so no OpenAI cost in this phase).
- Real ingestion, chunking, embeddings, search, extraction (Phases 1 and 2).
- Real UI screens, Figma, Storybook (Phase 5).
- Prometheus, Grafana, OpenTelemetry (Phase 6).
- Hosting and deployment (Phase 7).

## 5. Proposed answers for blueprint 5.3

| Decision | Proposal |
|---|---|
| Corpus and domain | Research papers on one narrow topic, 200 to 300 papers, CC BY licence only. Owner picks the topic |
| Ontology scope | 6 entity types, 8 predicates (blueprint default) |
| Extraction model | Small tier first (ADR-0001); measured on a 5% sample in Phase 2 |
| Gleaning passes | Compare 0 and 2 in Phase 2 |
| Community level | Default level 1; tested in Phase 3 |
| Neo4j | Community edition, self-hosted |
| Embeddings | Local bge-base-en-v1.5 |
| Judge | OpenAI main tier, answer order swapped, 10% human check (ADR-0001) |
| Sign-in (v1.5) | Deferred to v1.5 |
| Hosting | Deferred to Phase 7 |

## 6. Acceptance checks

| # | Check | Who verifies |
|---|---|---|
| A1 | `docker compose up -d` starts 5 containers and all report healthy | Owner on their machine (Claude checks what the cloud container allows) |
| A2 | `http://localhost:8000/api/v1/health` returns all services `ok` | Owner |
| A3 | `alembic upgrade head` creates every table from blueprint 4.4; `downgrade` removes them | Claude (tests) and owner |
| A4 | Fixture loader reports 10 of 10 documents, hashes match, every licence recorded | Claude (tests) |
| A5 | Ontology file validates against its schema | Claude (tests) |
| A6 | CI passes on the pull request | GitHub Actions |
| A7 | `git grep` finds no real secrets; `.env` is ignored | Claude |
| A8 | README run steps work from a fresh clone | Owner |

## 7. Plan (small steps)

1. Phase docs and folder structure.
2. Docker Compose with health checks.
3. FastAPI skeleton with health endpoint and tests.
4. Postgres migration and test.
5. Ontology file and fixture corpus with loader and tests.
6. Next.js placeholder and CI workflow.
7. Decision log, wireframes, WALKTHROUGH, README.
8. Demo to owner, fixes, then PR, merge and tag `phase-0` after approval.

## 8. Git

- Branch: `phase-0/setup`. Conventional commits. One PR into `main`.
- Tag after owner approval: `phase-0` (proposal; the blueprint does not name tags).
