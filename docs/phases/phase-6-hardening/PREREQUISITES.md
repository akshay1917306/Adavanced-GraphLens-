# Phase 6 prerequisites (owner)

| # | What | Status |
|---|---|---|
| 1 | Approve the plan and decisions D51 to D58 in `BRIEF.md`, especially D55 (no Prometheus or Grafana) and D58 (live answers wait for Phase 7) | **Owner to do** |
| 2 | Decide what happens to the test rows made by the single `local-demo` visitor in Phase 5 (a few conversations and one rating): delete them (recommended) or keep them | **Owner to decide** |
| 3 | Spend: $0 planned, no OpenAI calls | Confirmed earlier |
| 4 | A small download for `pip-audit` in a throwaway container (a few MB); asked again when needed | Later |
| 5 | About 1 hour at the end to try two browser profiles (history must not mix), delete, and the rate-limit message | Owner, later |
| 6 | Docker Desktop running | Check |

## Secrets

A new secret (`VISITOR_TOKEN_SECRET`) goes into your git-ignored `.env`. I will generate a random
value locally and never print it in chat; `.env.example` gets a placeholder only.
