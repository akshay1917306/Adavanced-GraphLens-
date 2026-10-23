# Phase 1 acceptance checks

Mark an item only after it was actually run. State where it was run.

## Build

- [x] License manifest lists source URL, license and date for every paper; only CC BY papers
      (25 papers; evidence is the ACL Anthology policy page, not a per-PDF check)
- [x] Ingest skips a file with the same content hash (run twice on the real 25 papers:
      25 new, then 0 new and 25 skipped)
- [x] Chunks are at most 450 tokens with 75 overlap and keep section metadata (CR-0002)
      (726 units, 17 to 450 tokens, average 308; sections kept in `documents.metadata`, see D16;
      3 units, 0.4%, still exceed bge's 512 tokens)
- [x] Embeddings stored in Qdrant (dense and sparse); re-running adds nothing new
      (726 points; second run: 0 embedded, 726 skipped; first run took 282 s on the owner's PC;
      3 units cut at 512 model tokens)
- [x] Baseline answer returns citations that point to real text unit IDs
      (the model cites passage numbers; each number maps to a unit ID; numbers that match no
      passage are flagged. This checks that the numbers exist, not that the passage supports
      the sentence)
- [ ] A failed run resumes without repeating finished work
- [x] Context size, retries, timeouts and a per-run cost cap are enforced
      (context 3000 tokens, output 500, question 1000 characters, timeout 60 s, 2 retries,
      `eval-run --max-cost-usd`. Not enforced: the daily cap `LLM_DAILY_COST_CAP_USD`)
- [x] Evaluation set v0: 30 local and 10 global questions, reviewed by the owner
      (machine-checked: 40 questions, 25 evidence units, every quote found in the corpus text;
      the owner answered "all OK" in chat on 2026-10-24, with no per-question notes in
      `data/eval/v0/REVIEW.md`; loaded into `eval_sets` and `eval_questions`)
- [x] Baseline results table recorded with model IDs, date and cost
      (`data/eval/v0/results/baseline-2026-10-23.md`: correct 70% overall, 93% local, 0% global;
      cost $0.05245; model `gpt-4.1-mini-2025-04-14`)

## Tests

- [x] Unit tests for ingest steps: PDF reading, cleaning, chunking, hashing, duplicates
      (retrieval merge and citation IDs come with their steps)
- [x] Negative tests: empty file, corrupt PDF, not a PDF, encrypted PDF, scanned PDF, too large,
      too many pages, duplicate file, unlicensed paper, changed file, NUL characters,
      one bad paper does not stop the batch
- [x] OpenAI calls mocked in routine tests and labelled as mocks (`FakeLlm`, `FakeEmbedder`)
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
