# Phase 1 acceptance checks

Mark an item only after it was actually run. State where it was run.

## Build

- [ ] License manifest lists source URL, license and date for every paper; only CC BY papers
- [ ] Ingest skips a file with the same content hash (run it twice, document count unchanged)
- [ ] Chunks are about 600 tokens with 100 overlap and keep section metadata
- [ ] Embeddings stored in Qdrant (dense and sparse); re-running adds nothing new
- [ ] Baseline answer returns citations that point to real text unit IDs
- [ ] A failed run resumes without repeating finished work
- [ ] Context size, retries, timeouts and a per-run cost cap are enforced
- [ ] Evaluation set v0: 30 local and 10 global questions, reviewed by the owner
- [ ] Baseline results table recorded with model IDs, date and cost

## Tests

- [ ] Unit tests: parsing, hashing, chunking, retrieval merge, citation IDs
- [ ] Negative tests: empty file, corrupt PDF, duplicate file, unlicensed paper, over-long text
- [ ] OpenAI calls mocked in routine tests and labelled as mocks
- [ ] One small live call to confirm the key and model work (cost shown first)
- [ ] `ruff` and `pytest` pass; CI green

## Docs

- [ ] WALKTHROUGH.md written and honest about results and limits
- [ ] README updated (status, commands, URLs, env variable names)
- [ ] STATUS.md up to date

## Owner review

- [ ] Owner reproduced the run steps on their own machine
- [ ] Owner approved the questions and the results table
