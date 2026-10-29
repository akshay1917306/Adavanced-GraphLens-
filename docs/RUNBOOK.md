# GraphLens runbook

For one person running GraphLens on one computer with Docker. All commands run from the repository
folder (the one that holds `docker-compose.yml`). The `scripts/*.sh` files are bash scripts: on
Windows run them in **Git Bash**; they also work on Linux and macOS. `check.sh` needs Python 3 on the
host.

## Start, stop, health

| Task | Command |
|---|---|
| Start (saved answers, no model key needed) | `docker compose up -d --build` |
| Start with live answers | set `ANSWER_MODE=live` and the model key in `.env`, then `docker compose --profile live up -d --build` |
| Stop (keeps the data) | `docker compose down` |
| Stop and **delete all data** | `docker compose down -v` (never do this without a backup) |
| State of the services | `docker compose ps` |
| Health of the databases | open `http://localhost:8000/api/v1/health` (all four must say `ok`) |
| Counts and one real question | `bash scripts/check.sh` (ends with `CHECK OK`) |
| Logs of one service | `docker compose logs --tail 100 api` (or `web`, `search`, `neo4j` ...) |

The web screen is `http://localhost:3000`. Every port is bound to 127.0.0.1 only.

## Backup

```bash
bash scripts/backup.sh
```

Writes `backups/<date-time>/` with `postgres.dump`, `neo4j.dump`, `qdrant.tar.gz` and `SHA256SUMS`.
Takes about one to two minutes. What it does and why:

- **Postgres**: `pg_dump` while the database runs.
- **Neo4j**: Community Edition can only dump a stopped database, so the script stops Neo4j, the API,
  the web and the search service, dumps, and starts everything again. **The site is down for that
  time.**
- **Qdrant**: the whole storage folder as a tar archive while Qdrant is stopped (a few seconds). This
  keeps the collection and the alias `units_live` together.
- **Redis is not saved**: it only holds rate-limit counters and the daily cost counter, which start
  again from zero.
- The folder `backups/` is git-ignored. The backup holds the user data (history, saved answers) and
  the whole corpus index, so keep it somewhere private; a copy on the same disk does not protect
  against a broken disk, so copy it to another drive too.
- `.env` (keys) is **not** in the backup. Keep your own copy in a safe place.

## Restore

```bash
bash scripts/restore.sh backups/<date-time>
```

It checks the checksums, asks you to type `restore`, then **replaces** the data of all three stores
and starts the stack. Wait about a minute and run `bash scripts/check.sh`.
`--yes` as the second argument skips the question.

Restore on a new computer: install Docker, clone the repository, copy `.env.example` to `.env` and
fill it in (the `POSTGRES_*` and `NEO4J_PASSWORD` values must be set; the same values as before are
not needed because the data is loaded into the new databases), then run the restore.

### What was actually tested (2026-10-29)

A backup of the real stack (751 text units, 1,545 entities, 193 communities) was restored into a
**second, empty stack** with new volumes (project name `gltest`, other ports). Afterwards the counts
were identical to the original (Postgres 751 units and 35 documents, Neo4j 1,545 and 193, Qdrant 751
points and the alias), the API health was `ok`, a saved question answered with HTTP 200 and the web
screen answered. The test stack was then deleted. Not tested: restoring over a stack that already
has newer data, restoring on another operating system, a backup taken while a live answer is running.

## Common errors

| What you see | Cause and fix |
|---|---|
| `no configuration file provided: not found` | You are in the wrong folder. `cd` into the repository folder. |
| `set POSTGRES_USER in .env` and similar | `.env` is missing or incomplete. Copy `.env.example` to `.env` and fill it in. |
| The screen says "No answer: replay mode only knows the saved example questions" | Normal in replay mode. Pick an example, or switch to live mode (needs the model key). |
| API replies `503 storage_unavailable` | A database is down. `docker compose ps`, then `docker compose up -d`; if one keeps restarting read its log. |
| `429 rate_limited` or `daily_limit` | Rate limit or the daily cost cap (`LLM_DAILY_COST_CAP_USD`) reached. Wait, or raise the cap on purpose in `.env` and restart the API. |
| `504 engine_timeout` / `503 busy` in live mode | The search service took too long or is full. Try again; read `docker compose logs search`. |
| Docker says the engine pipe is missing | Docker Desktop is not running. Start it and wait until it says "running". |
| Port already in use | Another program uses that port. Change the `*_PORT` value in `.env`. |
| Neo4j does not become healthy after a restore | Give it a minute; then `docker compose logs neo4j`. If it says the store is damaged, restore again from an older backup. |

## Keys and spending

The OpenAI key lives only in `.env` (git-ignored). Spending is limited three ways: the monthly limit
you set in the OpenAI account, `LLM_DAILY_COST_CAP_USD` in `.env` (default 1.0), and the rate limits
of the API. If a key may have leaked, delete it in the OpenAI dashboard first, then put a new one in
`.env` and restart (`docker compose up -d`).
