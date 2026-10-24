# Phase 3 prerequisites (owner)

| # | What | Status |
|---|---|---|
| 1 | Approve the plan and the decisions D27 to D32 in `BRIEF.md` | **Owner to do** |
| 2 | Spend cap for Phase 3: $2.00 (D32) | **Owner to approve** |
| 3 | OpenAI monthly limit of at least about $5 in the OpenAI dashboard (open since Phase 2) | **Owner to do** |
| 4 | Decide: add 10 more global questions (about 30 minutes of your review)? Recommended | **Owner to decide** |
| 5 | Later: about 30 minutes to rate 20 communities (1 to 5) and check 10 judge verdicts | **Owner to plan** |
| 6 | Stable internet for the image build (the Leiden library adds heavy packages) | Check |
| 7 | Docker Desktop running with 6 GB or more memory | Check |
| 8 | The corpus stays at the 25 development papers | Decided |

## Money

Claude shows a dry-run estimate and waits for a "yes" before each paid batch (report
generation, global evaluation). `LLM_DAILY_COST_CAP_USD` is still not enforced by code; the
per-run cap is. Leiden, embeddings and Neo4j are local and free.

## Open from Phase 2 (not blocking)

D5 (extraction model) and D6 (gleaning) are not decided because the precision of the extras was
never measured. `idx2-full-g0` and `idx2-full-g2` run records stay `running`.
