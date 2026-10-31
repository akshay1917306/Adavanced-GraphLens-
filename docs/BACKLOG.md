# Backlog

Ideas that are outside the current phase. Nothing here is approved.

- Add Neo4j constraints and indexes as versioned Cypher scripts (blueprint 4.3, 4.9). Planned for Phase 2.
- (Done in Phase 1) Prefect and the `pipeline/` package.
- (Done in Phase 1, with real corpus PDFs instead) PDF parser. A small PDF test fixture is built in the tests.
- Add a pre-commit secret scanner (for example gitleaks) to CI.
- Replace the plain-text wireframes with Figma designs. Phase 5.
- Upgrade Prefect and drop the FastAPI pin (D21) when a Prefect release supports FastAPI 0.156 or newer.
- Add CI for the `pipeline/` folder (ruff and the test suite with Postgres and Qdrant containers).
- Enforce the daily LLM cost cap `LLM_DAILY_COST_CAP_USD` (not used by any code yet).
- Add `--replace` to re-ingest a corpus after the chunker changes, instead of deleting rows by hand.
- Harder evaluation questions from full paper text (not only abstracts) and a second judge or human check.
- Compare the quantised bge model with the full-precision one on the evaluation set (D19).
- `CITES` edges: parse the reference list (it is cut today) and link papers inside the corpus.
- Add `--replace` to ingest so a changed chunker does not need hand-written SQL (done by hand again for CR-0003).
- Bigger corpus (100 to 250 papers) and an `add-papers` incremental command; pypdf upgrade with re-extraction (D59, D71, D72). Dropped from v1.5 because the OpenAI limit cannot be raised; needs a new estimate and approval.
- Email sending for password reset or magic links (costs money); recovery codes are used instead (D70).
- Global search answers cite communities ([C7]) but not papers. The owner's review (Phase 3 verdicts V09, V10, 2026-10-31) found that naming the paper ID of each claim makes answers easier to trust. Idea: add the papers behind each cited community to the answer. Nothing approved.
