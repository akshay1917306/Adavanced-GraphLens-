# Phase 6 load test

Run on 2026-10-28 on the owner's laptop (Docker Desktop: 12 CPUs, 8 GB memory for all containers
together). **No model was called and nothing was spent**: the first test uses replay answers, the
second uses the real databases and the local embedding model but stops before the model call.

## Test 1: the replay path (API and web server)

Each row sends 60 `ask` requests, with the stated number in flight at the same time, from 10
different visitors (each with a real signed token). Every request is validated, answered from the
saved file, written to Postgres (conversation, messages, metadata, citations) and counted in Redis.
To make this possible the rate limits were raised for the run only (set through environment
variables, then restored to 10 asks per minute per visitor and 30 per address).

| At once | Straight at the API: errors | median | p95 | max | requests per second |
|---|---|---|---|---|---|
| 1 | 0 of 60 | 19 ms | 35 ms | 57 ms | 47 |
| 3 | 0 of 60 | 37 ms | 61 ms | 67 ms | 77 |
| 10 | 0 of 60 | 157 ms | 220 ms | 278 ms | 60 |

| At once | Through the web server: errors | median | p95 | max | requests per second |
|---|---|---|---|---|---|
| 1 | 0 of 60 | 32 ms | 59 ms | 87 ms | 28 |
| 3 | 0 of 60 | 44 ms | 60 ms | 66 ms | 66 |
| 10 | 0 of 60 | 156 ms | 226 ms | 239 ms | 62 |

## Test 2: the retrieval path of local search (no model call)

Each row runs the 30 hard questions twice (60 runs) through link, expand, rank and context
assembly against the real Neo4j, Qdrant and Postgres, with threads in one process (the databases
and the embedding model are shared, as they would be inside one server process).

| At once | Failed | Refused | median | p95 | max | questions per second |
|---|---|---|---|---|---|---|
| 1 | 0 of 60 | 0 | 495 ms | 566 ms | 656 ms | 2.1 |
| 3 | 0 of 60 | 0 | 1,077 ms | 1,321 ms | 1,419 ms | 2.8 |
| 10 | 0 of 60 | 0 | 4,698 ms | 5,889 ms | 6,521 ms | 2.1 |

Peak memory of that process: about 950 MB.

## What this shows

- The API, the database writes and the web proxy are not a bottleneck: 10 at once still answers in
  well under a quarter of a second, with no error.
- The retrieval part is the slow part and it does not scale with more threads: throughput stays at
  about 2 to 3 questions per second, so latency grows almost in step with the number in flight (the
  work is mostly computing in Python, which threads do not run in parallel).
- Three at once is comfortable (p95 1.3 s before the model call). Ten at once is not: retrieval alone
  has a p95 of 5.9 s, and a model call of a few seconds comes on top, so the blueprint's target of
  p95 under 8 s per local question would be missed at that load.
- The per-visitor and per-address limits make ten simultaneous heavy questions from one person
  impossible; ten different people at the same moment is the case that would be slow.

## What this does not show

- No test with a real model call, so the end-to-end time of a live answer under load is unknown
  (it needs the OpenAI key and the Phase 7 live wiring).
- The retrieval test ran in the pipeline process, not inside the API server, which does not contain
  the search code yet.
- Short runs on one machine with warm caches; no long soak test, no memory-growth check over hours,
  no test of the databases under failure.
- Global search, relate mode and the router were not part of the load test.

## If it needs to go faster (Phase 7)

Run the retrieval in several worker processes instead of threads, cache the question embedding for
repeated questions, and measure again with the real model call before choosing numbers.
