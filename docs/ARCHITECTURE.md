# Architecture

## The pieces

```
Browser
  │  http://localhost:3000
  ▼
web  (Next.js 16, React 19)  ── sets/reads the HttpOnly visitor cookie, nonce CSP,
  │                              route handlers forward /api/* (adds PROXY_SECRET)
  ▼
api  (FastAPI)  ── visitor token check, rate limits (Redis), daily cost cap (Redis),
  │                 32 KB body limit, request ids, history/saved/feedback (Postgres)
  │
  ├─ ANSWER_MODE=replay ─► api/app/replay_answers.json (5 answers + 2 refusals)
  │
  └─ ANSWER_MODE=live ──► search  (internal service, same image as the pipeline, no host port)
                             │  router → local | relate | global | plain RAG
                             │  4 slots, 5 s queue, 40 s deadline, retries on free reads,
                             │  model circuit breaker, citation check
                             ├─► Postgres  (documents, text units, extraction cache, runs)
                             ├─► Neo4j     (entities, relations, communities, vector indexes)
                             ├─► Qdrant    (passage vectors, alias "units_live")
                             └─► OpenAI gpt-4.1-mini (the only paid call)
```

Redis holds only counters. Every host port is bound to 127.0.0.1.

## Building the knowledge (offline, command line `pipeline`)

1. **Ingest**: read PDFs, clean, detect sections, split into passages of 450 tokens (75 overlap) → Postgres.
2. **Embed**: local `BAAI/bge-base-en-v1.5` (dense) plus sparse vectors → Qdrant. No API cost.
3. **Extract**: the model reads each passage against the ontology and returns entities and relations
   with an evidence quote; results are cached by content hash, so a repeat run costs nothing.
4. **Resolve**: merge duplicate entities; every decision is stored; a guard blocks risky merges.
5. **Load graph**: Neo4j nodes and relations keep their source passages and evidence quotes.
6. **Communities**: hierarchical clustering (193 communities), a cited report for each, embedded.

## Answering

- **Local**: link entities (name match plus vector index, thresholds in `linking.py`; a model name
  with an unknown version is refused before the model is called), expand up to 2 hops, rank with
  PageRank, fill an 8,000-token context (split 45/25/20/10 between the kinds of evidence, see `localcontext.py`),
  ask the model for a cited answer, then check every citation.
- **Relate**: shortest paths between two entities, then a short explanation that may use only the path.
- **Global**: choose relevant community reports, answer from each (map), combine (reduce).
- **Router**: rules first (accuracy 92%); a small model only when the rules are unsure (97% together).
- **Refusal**: if the evidence is missing, or the model says so in plain words, the answer is a refusal.

## Security design in one paragraph

Deny by default; authorization on the server (a signed visitor token `v1.<id>.<expiry>.<HMAC>` in an
HttpOnly cookie, each visitor sees only their own rows); untrusted text (papers, questions, answers)
is always data, never instructions, never HTML; the model never writes Cypher; fixed query templates
only; secrets only in `.env`; logs hold request ids, modes and timings, never question text;
failures return a typed error, never a stack trace. See [ERROR_HANDLING.md](ERROR_HANDLING.md) and
[Phase 6 AUDIT](phases/phase-6-hardening/AUDIT.md). It has not had an outside security review.

## Why these choices (details in [DECISIONS.md](DECISIONS.md))

- Postgres is the source of truth; Neo4j and Qdrant can be rebuilt from it (and from the extraction cache).
- A separate search service (CR-0004) keeps the heavy model and database libraries out of the API
  image, whose dependencies are pinned differently. We did not put the search code inside the API
  because the Neo4j driver and FastAPI versions conflict between the two.
- `gpt-4.1-mini` for all model calls ($0.40 / $1.60 per million tokens) because the budget is small.
  We did not try a larger model; the measured misses are about context size, not wording.
- Replay mode is the default so that anyone can run the project without a key and without cost.
