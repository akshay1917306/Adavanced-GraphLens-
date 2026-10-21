# Phase 0 checklist

Legend: [x] done and verified by Claude in the build environment, [ ] not done or
needs the owner.

## Build
- [x] Folder structure, `.gitignore`, `.editorconfig`, `.gitattributes`, `.env.example` (placeholders only)
- [x] `docker-compose.yml`: Postgres 16, Neo4j 5.26 Community, Qdrant 1.15, Redis 7.4, API; ports bound to 127.0.0.1
- [x] API `/api/v1/health` reports each service, returns 503 when one is down
- [x] Alembic migration 0001: all 23 tables and 10 indexes from blueprint 4.4
- [x] Ontology `ontology/research_v1.yaml` and validator
- [x] Synthetic fixture corpus (10 documents) with manifest, hashes, licences, trust levels
- [x] Fixture loader (`--check`, `--load`), idempotent, one transaction
- [x] Next.js placeholder page showing service status
- [x] GitHub Actions CI: ruff, pytest (with Postgres), eslint, next build, typecheck, compose config
- [x] Decision log (`docs/DECISIONS.md`), ADR-0001, wireframes, backlog

## Acceptance checks (from BRIEF section 6)
- [x] A1 `docker compose up -d` starts 5 healthy containers (Claude, sandbox)
- [x] A2 `/api/v1/health` returns all `ok` (Claude, sandbox); 503 with Neo4j stopped
- [x] A3 upgrade creates 23 tables, downgrade removes them (pytest)
- [x] A4 fixture loader: 10 of 10 valid, tampered or missing files detected (pytest)
- [x] A5 ontology validates; bad ontologies rejected (pytest)
- [ ] A6 CI green on the pull request (needs push access)
- [x] A7 no real secrets in the repository; `.env` ignored
- [ ] A8 README steps work on the owner's machine (owner)

## Owner review
- [ ] Owner runs the manual checks in WALKTHROUGH.md
- [ ] Owner confirms D1 (phase plan) and ADR-0001
- [ ] Owner approves Phase 0
- [ ] PR merged, tag `phase-0` pushed and verified
