# Phase 1: Baseline RAG and evaluation set v0

Source: blueprint v1.0 sections 1.3 (G1, G2, G6, G11), 2.5, 2.10, 5.1.

## Goal

Build the plain vector-search RAG (no graph) and measure it. This is the score GraphRAG
must beat in later phases. Without a baseline, nobody can show that the graph helps.

## Requirements covered

| ID | Requirement | In this phase |
|---|---|---|
| G1 | Ingest documents, dedupe by content hash | PDF and text first; HTML and Markdown if the corpus needs them |
| G2 | Split into text units with section metadata | About 600 tokens, 100 overlap |
| G6 | Embed text units | Text units only (entities and reports come later) |
| G11 | Baseline vector RAG mode | Hybrid (dense plus sparse) retrieval and a cited answer |

NFR touched: cost control (per-run cap, estimate before big runs), reproducibility
(record model, prompt and config on every run), reliability (resumable, idempotent stages).

## Corpus (decision D3, closed)

Question answering (QA) methods and benchmarks, from the ACL Anthology. Only papers
whose license is CC BY are used. A license manifest records, for each paper: source URL,
license, and download date. A paper without a clear license is not added.

Size: 20 to 30 papers for development first. The full 200 to 300 comes later and only
after a cost estimate is approved.

## What we will build

1. License manifest and a small download script (polite rate limit).
2. Ingest: parse, content hash, duplicate skip, raw file stored, row in `documents`.
3. Chunking with section metadata, stored in Postgres.
4. Local embeddings (bge-base-en-v1.5) into Qdrant, dense and sparse.
5. Baseline answer: retrieve, build a bounded context, ask the OpenAI model, return the
   answer with citations to text unit IDs.
6. A Prefect flow with checkpoints so a failed run resumes without repeating work.
7. Evaluation set v0: 30 local and 10 global questions with expected supporting text.
8. Baseline results table and a cost record.

## Not in this phase

Entity extraction, Neo4j graph, communities, router, relate mode, UI, accounts.

## Open items

- Exact OpenAI model IDs are chosen at the start of building step 5, after checking
  OpenAI's official model list and pricing that day (ADR-0001). Recorded in an addendum.
- Questions for the evaluation set are drafted by Claude from the real papers and
  **reviewed by the owner**, because the owner is the judge of what is a good question.
