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
