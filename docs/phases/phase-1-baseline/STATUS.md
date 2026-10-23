# Phase 1 status

Last updated: 2026-10-24

## State

**Built and verified by Claude on 2026-10-24. Waiting for the owner's review.** All 8 steps
are done: corpus, ingest, chunking, embeddings, baseline answer, Prefect flow, evaluation set
(approved), baseline results. WALKTHROUGH.md and the root README are written. The phase is
**not approved, not pushed, not tagged**. Local branch `phase-1/baseline`; nothing from
Phase 1 is on GitHub.

Final checks run on 2026-10-24 on the owner's machine: 106 tests pass, `ruff` clean,
`eval-verify` 0 problems, API health ok, data intact (726 units, 726 vectors, 40 questions,
40 results). The CI job for `pipeline/` is written but has **not run on GitHub**.

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

## Evaluation set v0 draft (2026-10-24, Claude)

- `data/eval/v0/questions.json`: 30 local questions (25 single-paper, 5 using two papers) and
  10 global questions. Each has a reference answer and exact evidence quotes. Status: DRAFT.
- `docker compose run --rm pipeline eval-verify` checks every quote against the database:
  40 questions, 25 evidence units, 0 problems. (A first draft had 1 wrong quote; it was
  caught by this check and fixed.)
- `data/eval/v0/REVIEW.md` is the page for the owner to read and mark OK, CHANGE or DROP.
- Limits, stated plainly: the questions come from the **abstracts** only, so they are mostly
  fact lookups and may be easy for the baseline; only 5 are real two-paper questions (the
  blueprint expects a harder multi-hop benchmark of 50 questions later); the questions were
  written by an AI, so only the owner's review makes them a trustworthy answer key; the 10
  global reference answers are summaries of abstract quotes, not a complete list.
- Tests: 84 pass in Docker (12 new for the question checker). `ruff` clean.

## Evaluation runner (2026-10-24, Claude)

- Owner reviewed `REVIEW.md` and answered "all OK" in chat (no per-question edits were written
  in the file). All 40 questions are marked `approved` and loaded into `eval_sets` and
  `eval_questions` (30 local, 10 global).
- New commands: `eval-verify`, `eval-review`, `eval-load`, and `eval-run` (with `--dry-run` and
  `--max-cost-usd`). The run measures supporting-fact coverage (evidence quotes found in the
  passages sent), citation-number validity, correctness by an LLM judge, cost and latency,
  and stores everything in `eval_runs` and `eval_results`.
- Dry run (no model called): 40 questions, about 109k input and 9.6k output tokens, estimated
  **$0.059** for answers plus judge on `gpt-4.1-mini`. Default cost cap `--max-cost-usd 0.25`.
- Tests: 103 pass in Docker (19 new, answers and judge are labelled mocks). `ruff` clean.
- Not done: the live 40-question run waits for the owner's approval of the cost. Judge caveat:
  the judge is the same model family as the answerer; the owner should spot-check 4 answers.

## Baseline results (live run, 2026-10-24 local time, run by Claude with the owner's approval)

Run id `209e17c2-a537-4057-bf32-56f5adfb471a`, git `2968644`, model `gpt-4.1-mini` for answers
and judge, 40 of 40 questions, **total cost $0.05245** (estimate was $0.059; cap was $0.25),
133 seconds, latency p50 1.7 s and max 4.2 s. Files: `data/eval/v0/results/baseline-2026-10-23.md`
and `.json` (the file date is the container's UTC date).

| | All | Local (30) | Global (10) |
|---|---|---|---|
| Correct (LLM judge) | 70% | 93% | 0% |
| Correct or partial | 100% | 100% | 100% |
| Supporting-fact coverage | 68% | 88% | 9% |
| Citation numbers valid | 100% | 100% | 100% |

What this means, with limits:
- **Plain RAG is strong on single-fact questions and weak on corpus-wide questions.** All 10
  global questions were only "partial", and the retrieved passages held only 9% of the evidence.
  That gap is what GraphRAG (communities and global search) must close in Phases 3 and 4.
- **The local score is probably too high to be useful for comparison.** The questions were
  written from abstracts, so they are easy; 93% leaves little room to show a gain. The harder
  benchmark (50 multi-hop questions) comes later.
- **Judge noise.** Spot-check by Claude of 4 answers: L14 and L26 were judged "partial" only
  because the answer added true extra detail (the instructions say extra detail is fine), so the
  judge was too strict; L23 was "correct" and its coverage 0% only because the exact quote was
  in another chunk of the same paper; G01 "partial" looks right. The judge is the same model as
  the answerer. The owner's own spot-check of these four is still wanted.
- Citation numbers valid means the numbers exist, not that sentences are supported.
- Only 25 papers; results do not transfer to the real corpus.

## Prefect flow (2026-10-24, Claude)

- `docker compose run --rm pipeline index`: one flow, two tasks (ingest, embed), each with 2
  retries and 5 second pauses. Real-data run on the 25 papers: nothing new, 52 seconds, state
  Completed.
- Dependency facts: Prefect 3.8.8 (Apache-2.0) adds 78 packages (61 to 139) and about 170 MB;
  the image is now 1.3 GB. Prefect 3.8.8 needs FastAPI 0.139 or newer, but its server code
  breaks with FastAPI 0.156 or newer (`Body(min_items=...)`), so FastAPI is pinned to 0.143.0
  (D21). Prefect telemetry is switched off in the image (`DO_NOT_TRACK=1`,
  `PREFECT_SERVER_ANALYTICS_ENABLED=false`, checked inside the container).
- Prefect's own run records are temporary (inside the container). The database is the truth.
- Not done: writing `index_runs` and `run_stages` rows. They describe versioned index runs and
  a quality gate, which start in Phase 2; using them now would bend their meaning.
- Tests: 106 pass in Docker (3 new flow tests with real Postgres and Qdrant, mock embeddings).

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

## Exact next action (after the owner's review)

1. Owner follows "How to run it" and "How to test it" in WALKTHROUGH.md on their machine and
   reports problems. Owner also reads the four spot-check answers (L14, L26, L23, G01).
2. If approved: Claude pushes `phase-1/baseline`, opens a PR, waits for CI (the new `pipeline`
   job is untested), fixes what fails, merges (fast-forward), tags `phase-1`, verifies on
   GitHub, then plans Phase 2. Never force-push.

## Older notes (kept for history)

1. (done) Embeddings, see above.
2. (done) Baseline answer, see above.
3. (done) Evaluation set v0 approved and loaded; runner built and dry-run.
4. (done) Live baseline run, results above. To repeat it:
   `$env:GIT_SHA = git rev-parse --short HEAD`, then
   `docker compose run --rm -v "$PWD/data/eval/v0/results:/out" pipeline eval-run`.
   The owner spot-checks the four answers listed in the results discussion.
5. (done) Prefect flow for ingest and embed.
6. Phase docs: WALKTHROUGH.md, root README update, notebook notes, final completion report.
   Also decide with the owner: CI for the `pipeline/` folder (the existing CI covers api, web
   and compose only), and how the owner re-runs everything on their own machine.
   Then stop for the owner's review; nothing is pushed until the owner says so.
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
