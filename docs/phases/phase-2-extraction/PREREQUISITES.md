# Phase 2 prerequisites (owner)

| # | What | Status |
|---|---|---|
| 1 | Decision: front-matter unit (option A) | Done, 2026-10-24 |
| 2 | `CITES` goes to the backlog | Assumed; tell Claude if you disagree |
| 3 | OpenAI monthly limit of at least about $5 in the OpenAI dashboard | **Owner to do** |
| 4 | About 2 hours later to review labeled data (30 text units, candidate pairs) | **Owner to plan** |
| 5 | Docker Desktop with 6 GB or more memory (Neo4j is running already) | Check |
| 6 | The corpus stays at the 25 development papers | Decided |

## Money

Claude shows a dry-run estimate and waits for a "yes" before the full extraction. The daily cap
variable `LLM_DAILY_COST_CAP_USD` (1.00) is not enforced by any code yet; Phase 2 adds a
per-run cap. Neo4j, embeddings and the entity matching are local and free.
