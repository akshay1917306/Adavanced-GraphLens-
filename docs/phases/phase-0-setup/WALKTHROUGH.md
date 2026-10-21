# Phase 0 walkthrough: Setup and decisions

## 1. What we built

A working, empty skeleton of GraphLens:

- Four databases running in Docker: **Postgres** (records), **Neo4j** (the knowledge
  graph), **Qdrant** (vector search), **Redis** (caching and rate limits later).
- A small **API** (FastAPI) with one endpoint, `/api/v1/health`, that says which
  databases are reachable.
- The full **Postgres schema** from the blueprint (23 tables), created by a migration.
- The **ontology**: the list of entity types (Paper, Author, Method...) and
  relationships (PROPOSES, USES...) that the graph may contain.
- A **fixture corpus**: 10 short, made-up research papers used for tests.
- A **web placeholder** (Next.js) that shows the health status.
- **CI** (GitHub Actions) that runs lint and tests on every pull request.

Nothing answers questions yet. That starts in Phase 1.

## 2. How it works, step by step

1. `docker compose up` reads `docker-compose.yml` and `.env`, then starts five
   containers. Each one has a *health check* (a small command Docker runs to see if
   the service is ready).
2. The API container waits until the four databases are healthy. It then runs
   `alembic upgrade head`, which creates any missing tables, and starts the web server
   on port 8000.
3. When you open `/api/v1/health`, the API tries a tiny request to each database
   (for example `SELECT 1` on Postgres). Each result is `ok` or `unavailable`. If any is
   unavailable, the response code is 503, so monitoring tools notice.
4. `python -m app.fixtures --load` checks every fixture file against its SHA-256 hash
   (a fingerprint of the file), then writes the ontology, a corpus row, and 10
   document rows into Postgres in one transaction. Running it twice adds nothing new.
5. The web page asks the API for health **from the server side**, so the browser never
   needs to talk to the API directly.

**Example:** stop Neo4j with `docker compose stop neo4j`, reload the health URL, and
you see `"neo4j": "unavailable"` with status 503.

## 3. Important files

| File | Responsibility |
|---|---|
| `docker-compose.yml` | Defines the five containers, ports (localhost only), volumes, health checks |
| `.env.example` | List of settings with fake values. Copy to `.env` (git-ignored) |
| `api/app/main.py` | FastAPI app and the health route |
| `api/app/health.py` | One check per database; never logs error messages that could hold passwords |
| `api/app/config.py` | Reads settings from environment or `.env`; hides passwords |
| `api/alembic/versions/0001_initial_schema.sql` | The blueprint's SQL, copied without changes |
| `api/app/ontology.py`, `ontology/research_v1.yaml` | Ontology file and its validator |
| `api/app/fixtures.py`, `data/fixtures/research_v0/` | Fixture documents, manifest, and loader |
| `web/app/page.tsx` | Placeholder page |
| `.github/workflows/ci.yml` | CI jobs |
| `docs/DECISIONS.md`, `docs/adr/` | Decisions and change requests |

## 4. Tools and why

- We used **Docker Compose** because it starts all four databases with one command and
  the same versions on every machine. We did not install them directly on Windows
  because versions drift and removing them is messy.
- We used **FastAPI** (blueprint choice) because it is Python, fast, and validates
  inputs with Pydantic types. Flask is simpler but has no built-in validation.
- We used **Alembic** (blueprint choice) because every database change becomes a
  numbered, reversible file. Creating tables by hand cannot be repeated reliably.
- We used **uv** because it installs the exact Python version and locks every package
  version in `uv.lock`. pip with `requirements.txt` is the common alternative but is
  slower and does not manage Python itself.
- We used **Neo4j 5.26 Community** because 5.26 is the long-term support line and the
  Community edition is free. Enterprise adds clustering we do not need.
- We used **synthetic fixtures** because the rules say synthetic data during
  development, and because we know the true facts (`expected_relations.csv`), which
  lets Phase 2 tests measure extraction accuracy. Real papers come with the real corpus.
- We used **Next.js 16 + TypeScript** (blueprint choice). Only a placeholder for now.

## 5. How to run it

Use the **Ubuntu (WSL) terminal** in VS Code (Terminal > New Terminal, choose
"Ubuntu (WSL)").

**Terminal 1: databases and API**

```bash
cd ~/Adavanced-GraphLens-          # the repository folder
cp .env.example .env               # first time only; then change the two passwords
docker compose up -d --build       # first time takes several minutes (downloads)
docker compose ps                  # all five should say "healthy" or "running"
```

Open http://localhost:8000/api/v1/health. You should see
`{"status":"ok","services":{"postgres":"ok","neo4j":"ok","qdrant":"ok","redis":"ok"}}`.

Other URLs: Neo4j Browser http://localhost:7474 (user `neo4j`, password from `.env`),
Qdrant dashboard http://localhost:6333/dashboard, API docs http://localhost:8000/docs.

**Load the fixture corpus (same terminal):**

```bash
cd api
uv sync                                  # first time only
uv run python -m app.fixtures --load     # expect: Loaded ... now has 10 documents
```

**Terminal 2: web placeholder**

```bash
cd ~/Adavanced-GraphLens-/web
npm ci              # first time only
npm run dev
```

Open http://localhost:3000. You should see "GraphLens" and four services marked `ok`.

**Stop everything:** press `Ctrl+C` in terminal 2. In terminal 1 run
`docker compose down` (keeps data) or `docker compose down -v` (also deletes the
database data).

**Common errors**

| Error | Fix |
|---|---|
| `set POSTGRES_USER in .env` | You did not create `.env`. Run `cp .env.example .env` |
| `port is already allocated` | Another program uses that port. Change the port in `.env` (for example `POSTGRES_PORT=5433`) |
| `Cannot connect to the Docker daemon` | Start Docker Desktop and enable WSL integration for Ubuntu |
| Neo4j stays "starting" | Wait 1 minute; give Docker Desktop at least 6 GB memory |
| Health shows `neo4j: unavailable` after changing the password | Old data keeps the old password. Run `docker compose down -v` and start again |

## 6. How to test it

From `api/`:

```bash
uv run ruff check .        # code style
uv run pytest              # unit tests; database tests are skipped
```

Database tests need a **throwaway** Postgres, because they drop all tables:

```bash
docker run -d --name pgtest -e POSTGRES_USER=t -e POSTGRES_PASSWORD=t -e POSTGRES_DB=t -p 127.0.0.1:55432:5432 postgres:16.10-alpine
DATABASE_URL=postgresql+psycopg://t:t@127.0.0.1:55432/t uv run pytest
docker rm -f pgtest
```

Never point `DATABASE_URL` at a database you care about when running tests.

From `web/`: `npm run lint`, `npm run build`, `npm run typecheck`.

## 7. Actual results (2026-10-21, Claude's build environment, Linux)

- `pytest` with a throwaway Postgres: **16 passed**. Without a database: 14 passed, 2 skipped.
- `ruff check` and `ruff format --check`: clean.
- `npm run lint`, `npm run typecheck`, `npm run build`: clean.
- `docker compose up`: 5 containers healthy; health endpoint returned 200 with all
  `ok`; with Neo4j stopped it returned 503 and `neo4j: unavailable`; the API log
  showed only the error type (`ServiceUnavailable`), no password.
- Fixture load: 10 documents (9 medium trust, 1 low trust); running it again kept 10.
- Web page rendered the four services as `ok` (checked with a headless browser
  screenshot).
- Docker images in the build environment came from a Docker Hub mirror because of a
  rate limit; the API image was built with an extra certificate needed only there.
  Your machine uses the normal files.

**Not yet verified:** CI on GitHub (needs push access) and all steps on the owner's
Windows machine.

## 8. Limitations and open issues

- The fixture corpus is synthetic. The real corpus topic is still open (D3).
- No PDF fixture yet (added with the PDF parser in Phase 1).
- The API runs migrations on start-up. Fine for development; production will run them
  as a separate step (Phase 7).
- Neo4j memory is limited to 1 GB heap to fit a 16 GB laptop; we may raise it in Phase 2.
