# Phase 1 status

Last updated: 2026-10-23

## State

**In progress. Ingest, chunking, embeddings and the baseline answer are built and verified
(steps 1 to 5 of 8).** The evaluation set, results table and the Prefect flow are not started.

## Completed

- Phase 0 approved, merged to `main` (commit 2f4a51c), tagged `phase-0`. CI was green.
- D3 closed: QA papers from the ACL Anthology (ACL and EMNLP 2022 and 2023).
- Corpus manifest and download scripts: 25 papers downloaded (26.8 MB), all recorded as
  CC BY 4.0 on the basis of the Anthology policy page; hashes stored; re-run skips all.
- Owner's `.env` set: OpenAI key present, Postgres and Neo4j passwords changed, models
  `LLM_MODEL_SMALL` and `LLM_MODEL_MAIN` both `gpt-4.1-mini`.
- Live check (2026-10-23): one call to `gpt-4.1-mini` returned `ok` (15 tokens, about
  $0.00001). Key and model work.
- CR-0001 (simplified dashboard, small evidence graph kept) drafted, not yet approved as a CR.

## Verified on the owner's machine (2026-10-23, run by Claude)

- Owner enabled CPU virtualization and installed WSL; Docker engine 29.9.2 runs.
- `docker compose up -d --build`: 5 containers up and healthy (Postgres, Neo4j, Qdrant,
  Redis, API). `GET /api/v1/health` returned `ok` for all four services.
- Alembic revision `0001` applied; 24 tables exist (23 blueprint tables plus `alembic_version`).
- Fixture load: 10 documents (9 medium, 1 low trust).
- Note: the fixture loader needs `data/` and `ontology/` mounted into the container
  (the image does not contain them):
  `docker compose run --rm --no-deps -v "$PWD/data:/data:ro" -v "$PWD/ontology:/ontology:ro" api python -m app.fixtures --load`

## Done after the Docker fix (2026-10-23, run by Claude on the owner's machine)

- PDF library chosen by measurement: pypdf (D15). `fonttools` added so pypdf decodes math fonts.
- New `pipeline/` package (Docker image, pinned deps in `uv.lock`): PDF reading with safety
  checks, cleaning (ligatures, hyphens, page numbers, headers, References cut, Acknowledgements
  dropped, NUL removed), section detection, sentence-aware chunking, ingest into Postgres.
- Real run: 25 of 25 papers ingested. After CR-0002 (chunk size 450, overlap 75, because bge
  reads only 512 tokens): 726 text units (17 to 450 tokens, average 308). Second run added
  nothing (25 skipped). With the bge tokenizer, 3 units (0.4%) are still over 512 tokens.
- Tests: 39 pass in Docker (unit and integration; integration tests create and drop their own
  throwaway database). `ruff check` and `ruff format --check` clean.
- Found and fixed while testing: a PDF with NUL characters crashed the insert; false headings
  (list items, algorithm lines, wrapped headings) created tiny chunks.

## Embeddings (2026-10-24, run by Claude on the owner's machine)

- `docker compose run --rm pipeline embed`: 726 units embedded into collection
  `units_qa_v0_baseline_1` (dense 768, cosine; sparse BM25 with IDF). Alias `units_live` points
  at it. A second run embedded nothing. 3 units are longer than 512 model tokens (tail cut).
- Models: fastembed with the int8-quantised bge-base ONNX file (about 210 MB) and Qdrant/bm25
  (D19). The unquantised model was not compared; quality loss is not measured.
- Spot check with 3 searches (exact name, meaning without shared words, multi-step reasoning):
  dense, sparse and hybrid all returned the expected papers. This is a sanity check, not an
  evaluation; real scores come with evaluation set v0.
- Tests: 46 pass in Docker (7 new embedding tests: mocks for speed, plus a test with the real
  models). `ruff` clean. Image size 1.13 GB (models baked in so runs work offline).

## Baseline answer (2026-10-24, run by Claude on the owner's machine)

- `docker compose run --rm pipeline ask "..."`: hybrid search (dense and sparse, RRF) for 6
  passages, numbered context (3000 token budget), one `gpt-4.1-mini` call (500 token output
  cap, 60 s timeout, 2 retries, temperature 0), then a check that every `[n]` is a passage sent.
- Live check with 3 questions (cost shown by the program, about $0.0037 in total, about $0.0012
  per question): two answerable questions about ConditionalQA and KG-FiD returned cited answers
  with all citation numbers valid; "capital of Australia" was refused. I read the two answers
  and they match the topics of the cited papers, but I did not verify each sentence against its
  passage. Quality is only measured by evaluation set v0 later.
- The model sees passage text as untrusted data (system rule plus `<passage>` wrappers). This
  is tested with a mock, not proven against real attacks.
- Tests: 72 pass in Docker (26 new; the model is a labelled mock). `ruff` clean.
- Not done yet: the daily cost cap `LLM_DAILY_COST_CAP_USD` is not enforced by any code; the
  batch runner must enforce a per-run cap before the 40-question run.
- Pricing used for the cost line: OpenAI pricing page read on 2026-10-24
  (`gpt-4.1-mini`: $0.40 input and $1.60 output per 1M tokens).

## Known limits of the cleaning (not fixed, recorded honestly)

- Footnote text can land in the middle of a sentence (for example a "Data and code available at
  ..." footnote). Layout hyphen and real hyphen are indistinguishable (`multi-hop` can become
  `multihop`).
- Everything after the References heading is dropped, including appendices.
- 14 chunks are under 50 tokens (short section introductions). Acceptable for the baseline.
- Equations, tables and figures come through as plain text and may be messy.
- If the chunker changes, the corpus must be re-ingested (rows are skipped by content hash);
  the manual re-ingest I did deleted only the `qa_v0` rows. A `--replace` option is a later idea.

## Current work

Nothing running.

## Blockers

1. The first image download was very slow (about 0.3 to 1 MB/s). Later builds use the cache.
2. Dev tools (uv, Node, pytest, ruff, Python 3.11) are not installed on Windows. Pipeline
   code and tests will run inside Docker instead. Ubuntu on WSL is optional.

## Decisions waiting for the owner

- Approve CR-0001 (simplified dashboard).
- Confirm models for later: both lines are `gpt-4.1-mini` for now. Revisit before Phase 2
  with an extraction cost estimate (ADR-0001 addendum to record final IDs and date).

## Exact next action

1. (done) Embeddings, see above.
2. (done) Baseline answer, see above.
3. Evaluation set v0: 30 local and 10 global questions drawn from the 25 papers, each with
   the supporting passages. Claude drafts, the owner reviews. Then a batch runner with a cost
   cap, results table (correctness by an LLM judge with swapped order, citation check) and a
   cost record. Show the estimate and get the owner's approval before the batch.
4. Prefect flow with checkpoints (resume without repeating work), docs, README, walkthrough.
3. Prefect flow with checkpoints, then evaluation set v0 (30 local and 10 global questions,
   reviewed by the owner), and the baseline results table with cost.

Commands (from the repository folder, no Ubuntu needed):

    docker compose up -d                       # databases and API
    docker compose run --rm pipeline ingest    # parse, chunk and store the 25 papers
    docker compose run --rm pipeline embed     # local embeddings into Qdrant
    docker compose run --rm pipeline ask "Your question"   # plain RAG answer (costs about $0.001)
    docker compose run --rm --entrypoint pytest pipeline -q   # tests

## Local state

Branch `phase-1/baseline` has local commits only; nothing from Phase 1 is pushed yet.
`.env` is local and git-ignored.
