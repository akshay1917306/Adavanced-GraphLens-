# Phase 1 acceptance checks

Mark an item only after it was actually run. State where it was run.

## Build

- [x] License manifest lists source URL, license and date for every paper; only CC BY papers
      (25 papers; evidence is the ACL Anthology policy page, not a per-PDF check)
- [x] Ingest skips a file with the same content hash (run twice on the real 25 papers:
      25 new, then 0 new and 25 skipped)
- [x] Chunks are about 600 tokens with 100 overlap and keep section metadata
      (598 units, 17 to 600 tokens, average 371; sections kept in `documents.metadata`, see D16)
- [ ] Embeddings stored in Qdrant (dense and sparse); re-running adds nothing new
- [ ] Baseline answer returns citations that point to real text unit IDs
- [ ] A failed run resumes without repeating finished work
- [ ] Context size, retries, timeouts and a per-run cost cap are enforced
- [ ] Evaluation set v0: 30 local and 10 global questions, reviewed by the owner
- [ ] Baseline results table recorded with model IDs, date and cost

## Tests

- [x] Unit tests for ingest steps: PDF reading, cleaning, chunking, hashing, duplicates
      (retrieval merge and citation IDs come with their steps)
- [x] Negative tests: empty file, corrupt PDF, not a PDF, encrypted PDF, scanned PDF, too large,
      too many pages, duplicate file, unlicensed paper, changed file, NUL characters,
      one bad paper does not stop the batch
- [ ] OpenAI calls mocked in routine tests and labelled as mocks
- [x] One small live call to confirm the key and model work (2026-10-23, `gpt-4.1-mini`, 15 tokens)
- [ ] `ruff` and `pytest` pass; CI green (ruff and 39 pytest tests pass locally in Docker;
      CI is not set up for the pipeline folder yet)

## Docs

- [ ] WALKTHROUGH.md written and honest about results and limits
- [ ] README updated (status, commands, URLs, env variable names)
- [ ] STATUS.md up to date

## Owner review

- [ ] Owner reproduced the run steps on their own machine
- [ ] Owner approved the questions and the results table
