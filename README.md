# GraphLens (Advanced GraphRAG pipeline)

GraphLens turns a collection of research papers into a knowledge graph and answers questions by
following the graph, showing the evidence for every answer. It is built from the *Advanced GraphLens
Pipeline Blueprint v1.0* and runs on one computer with Docker.

> **Status: Phase 7 is approved, merged and tagged `phase-7` and `v1.0` (2026-10-29).** Phases 0 to 7
> are done. Phase 7 adds live answers, a final evaluation, backups and this documentation. **Three of the ten evaluation
> targets are missed** (listed below). It is a working, measured prototype on 25 papers, not a
> production system and not security-reviewed; do not expose it to the internet.

## What it does

Ask a question on the web screen. A router picks one of four ways to answer:

| Mode | For | How |
|---|---|---|
| Local search | a question about specific things | find the entities in the question, follow the graph up to 2 hops, rank by PageRank, put the best passages (8,000 tokens) in front of the model, check every citation |
| Relate | "how is A connected to B" | shortest paths in the graph, then a short cited explanation |
| Global search | "what are the main themes" | select, map and reduce over 193 cited community reports |
| Plain RAG | everything else, and the comparison answer | vector search over text passages |

Every answer shows its sources, a small evidence graph and a citation check (`verified`, `warning` or
`not checked`). When the evidence is missing it says so instead of guessing.

## Results (final evaluation, 2026-10-29)

Full tables, method and caveats: [docs/EVALUATION.md](docs/EVALUATION.md); reading and reasons:
[EVALUATION_NOTES.md](docs/phases/phase-7-launch/EVALUATION_NOTES.md). Corpus: 25 open-licence
papers, 751 text passages, 1,545 entities, 2,694 relations, 193 communities. Questions and gold
answers were drafted by Claude; the judge is the same model family as the answerer.

| Measure | Result | Target | |
|---|---|---|---|
| Local correctness, 30 hard multi-hop questions | **70%** (21 of 30; 95% interval 52 to 83%) | 75% | **missed** |
| Gap over plain RAG on the same questions | **+13.3 points** (plain RAG 57%) | +15 | **missed** |
| Time per local answer, p95 (one at a time) | **10.3 s** (median 5.4 s, slowest 26.6 s) | 8 s | **missed** |
| Citation support (20 answers, 115 claims) | 99.1% | 90% | met |
| Refusal of unanswerable questions | 10 of 10 on the development set (tuned there), 9 of 10 on fresh probes | 90% | met, with a caveat |
| Router accuracy (rules, then a small model) | 97 of 100 | 85% | met |
| Cost per local answer | $0.0031 | $0.03 | met |
| Easy questions, local vs plain RAG | 29 of 30 vs 28 of 30 | | little room to differ |
| Global search vs plain RAG | 100% on comprehensiveness and diversity, 45% on directness | | carried over from Phase 3, not re-run; answers are 3.4 times longer |
| Relate | 20 of 20 paths; 14 of 20 explanations pass the citation check | | nobody has read them for faithfulness |

Why the three misses: the graph reaches 95% of the right passages, but only about 57% of them fit
into the 8,000-token context, and 12,000 tokens did not help clearly (decision D68); the 15-point gap
is half a question short on a 30-question set; time is dominated by one model call that writes up
to 250 words. Details are in the evaluation notes.

## Run it

Needs Windows 11 or macOS, 16 GB RAM, about 10 GB free disk and **Docker Desktop**. Nothing else.
Run in the repository folder (Git Bash, PowerShell or any shell).

```bash
cp .env.example .env        # then put your own long random values for the passwords and secrets in it
docker compose up -d --build
```

This starts the databases, the API and the web screen with **saved answers** (replay mode: 5 real
answers and 2 refusals; any other question gets a clear "no saved answer" refusal). It needs no model
key and costs nothing. The databases start empty; the Ask screen still works because replay answers
are bundled. Checked from a fresh clone on 2026-10-29: one command, healthy in under a minute once
the images were built.

| URL | What you see |
|---|---|
| http://localhost:3000 | The Ask screen |
| http://localhost:8000/api/v1/health | `"status":"ok"` and four services |
| http://localhost:8000/docs | API documentation |
| http://localhost:7474 | Neo4j Browser (user `neo4j`, password `NEO4J_PASSWORD`) |

### Load the data

The graph and the index are **not in git**. Two ways:

1. **Restore a backup** (free): `bash scripts/restore.sh backups/<folder>` (see the
   [runbook](docs/RUNBOOK.md)). Tested into an empty stack on 2026-10-29, also from a fresh clone.
2. **Rebuild from the papers** (costs money): download the PDFs, then run the pipeline steps in the
   [Phase 1](docs/phases/phase-1-baseline/WALKTHROUGH.md) and
   [Phase 2](docs/phases/phase-2-extraction/WALKTHROUGH.md) walkthroughs. Extraction cost about
   $2.40 with `gpt-4.1-mini`; every command has `--dry-run` and `--max-cost-usd`.

### Live answers (uses your OpenAI key)

Put `OPENAI_API_KEY` in `.env` (never in chat or git), set `ANSWER_MODE=live`, keep
`LLM_DAILY_COST_CAP_USD` low, and set a monthly limit in your OpenAI account. Then:

```bash
docker compose --profile live up -d --build
bash scripts/check.sh
```

The API calls an internal search service (not published on any port). A local answer costs about a
third of a cent.

### Stop, back up, restore

`docker compose down` keeps the data; `down -v` deletes it. `bash scripts/backup.sh` and
`bash scripts/restore.sh` are described in the [runbook](docs/RUNBOOK.md), with health checks and
common errors.

## Tests

```bash
docker compose up -d postgres qdrant neo4j
docker compose run --rm --entrypoint pytest pipeline -q                    # 471 tests
docker compose run --rm --no-deps --entrypoint ruff pipeline check .
cd api && uv run pytest -q                                                 # 150 tests
cd web && npm run lint && npm run typecheck && npm run build
```

Tests that would call OpenAI use labelled fakes. CI (GitHub Actions) runs six jobs: api, web,
pipeline, compose (including the search service profile), secret scan, dependency audit.

## Documentation

- [Architecture](docs/ARCHITECTURE.md), [demo script (3 minutes)](docs/DEMO.md),
  [interview page](docs/INTERVIEW.md), [known limits](docs/LIMITS.md), [runbook](docs/RUNBOOK.md)
- [Evaluation](docs/EVALUATION.md), [decision log](docs/DECISIONS.md) (D1 to D68),
  [ADRs and change requests](docs/adr/), [error handling](docs/ERROR_HANDLING.md), [backlog](docs/BACKLOG.md)
- [Phases](docs/phases/README.md): every phase has a brief, checklist, status and walkthrough

## Phases

| Phase | State |
|---|---|
| 0 Setup and decisions | merged, tag `phase-0` |
| 1 Baseline RAG and evaluation set | merged, tag `phase-1` |
| 2 Extraction and graph | merged, tag `phase-2` |
| 3 Communities and global search | merged, tag `phase-3` |
| 4 Local search, router, relate, citation check | merged, tag `phase-4` |
| 5 API and Ask screen | merged, tag `phase-5` |
| 6 User data and hardening | merged, tag `phase-6` |
| 7 Evaluate and launch | approved, merged, tags `phase-7` and `v1.0`; owner review of the Phase 3/4 pages and the 10+10 spot-check are still open |

## Important limits (short)

Full list in [docs/LIMITS.md](docs/LIMITS.md). 25 development papers only. Questions drafted by
Claude, same-family judge, small sets. Optional accounts (email and password, unverified email, no second factor); anonymous use still works. No HTTPS, no monitoring.
Backups are manual and take Neo4j offline for about a minute. Two known advisories in the pipeline's
PDF libraries are accepted for now (D59). Not production-ready.
