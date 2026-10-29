# Phase 7 prerequisites (owner)

| # | What | Status |
|---|---|---|
| 1 | Approve the plan and decisions D60 to D66 in `BRIEF.md` (especially D60 local launch, D61 separate search service, D62 stay at 25 papers) | **Owner to do** |
| 2 | Spend cap for the phase: **$3.00** (D63); a shown estimate and your "yes" before every paid batch | **Owner to approve** |
| 3 | **OpenAI limit** in the dashboard: set the monthly limit to **$10** (this month's spend is already about $3.6, so $5 is too tight) | **Owner to do** |
| 4 | Put your key into the git-ignored `.env` as `OPENAI_API_KEY=...` and the model names `LLM_MODEL_MAIN` and `LLM_MODEL_SMALL` (`gpt-4.1-mini`). **Never paste the key in chat.** I will only check that the variable is set, never read its value | **Owner to do, at the start of step 1's live test** |
| 5 | About 3 hours in total to review: the Phase 3 community ratings and judge verdicts (20 + 10 items), the Phase 4 pages (30 hard questions, 20 relate pairs, 10 unanswerable), and the final spot-check (10 citations, 10 judge verdicts). You can split it across days | Owner, during the phase |
| 6 | Decide whether you want a public demo (D60 option B). If yes: a domain and a small server budget | **Owner to decide** |
| 7 | Docker Desktop running with at least 6 GB of memory; stable internet | Check |

## Money

I show a dry-run estimate and wait for your "yes" before each paid batch. Results are cached by a
hash of the input, so repeating a run is free. The daily cost cap (`LLM_DAILY_COST_CAP_USD`) and the
per-run caps stop a run cleanly.

## Secrets

`OPENAI_API_KEY` goes only into `.env`. It is never printed, logged, committed or sent to the
browser. If the key ever appears in a log or file by mistake, rotate it in the OpenAI dashboard.
