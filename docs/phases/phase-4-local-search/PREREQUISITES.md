# Phase 4 prerequisites (owner)

| # | What | Status |
|---|---|---|
| 1 | Approve the plan and the decisions D35 to D40 in `BRIEF.md` | **Owner to do** |
| 2 | Spend cap for Phase 4: $2.00 (D40) | **Owner to approve** |
| 3 | OpenAI monthly limit in the dashboard: at least $8 (this month's spend is about $3.3) | **Owner to do** |
| 4 | About 2 to 2.5 hours later to review the new questions (30 hard local questions, 10 unanswerable, 20 relate pairs, mode labels) | **Owner to plan** |
| 5 | Optional: the Phase 3 review pages (20 communities, 10 judge verdicts), still open | Owner, when there is time |
| 6 | Stable internet and Docker Desktop running with 6 GB or more memory | Check |
| 7 | The corpus stays at the 25 development papers | Decided |

## Money

Claude shows a dry-run estimate and waits for a "yes" before each paid batch (the evaluation
runs). `LLM_DAILY_COST_CAP_USD` is still not enforced by code; the per-run cap is. Entity
linking, graph expansion, PageRank and embeddings are local and free.

## Open from earlier phases (not blocking)

D5 (extraction model) and D6 (gleaning) are undecided. The Phase 3 community and verdict reviews
are open. Phase 2's entity-resolution F1 is 0.79 against 0.85 (accepted).
