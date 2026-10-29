# Phase 7: Evaluate and launch

Source: phase list (blueprint 5.1, name "Evaluate and launch"), the open items that Phases 1 to 6
left for this phase, and decisions D11, D12, D43, D55, D58, D59. The blueprint text is not in the
repository, so the scope below is built from those notes; where it is my reading, it is a decision
for you.

## Goal

Turn the working demo into a **finished v1.0** you can show and explain honestly:

1. the screen gives **live answers** (not only 7 saved ones), using your OpenAI key;
2. the numbers in the README come from **one clean final evaluation**, each compared with its target;
3. the system can be **started, backed up and restored** by someone who has only the README;
4. the weak spots found so far are **fixed or written down** with a reason.

This is the phase where **your OpenAI key is finally used** (your rule: key only at the end).

## Where we stand (measured, from the earlier phases)

| Area | Result | Target | Met? |
|---|---|---|---|
| Relation precision | 0.81 | 0.80 | yes |
| Entity resolution F1 | 0.79 | 0.85 | no (accepted in Phase 2) |
| Global search win rate vs plain RAG | 100% on 20 questions (answers 3.4 times longer, same-family judge) | measured | caveats |
| Local correctness, hard set (30) | 70% vs baseline 53% (+17 points) | at least 75% and +15 points | points yes, 75% no |
| Citation support | 98% of 124 sampled citations | at least 90% | yes |
| Refusal on unanswerable | 80% (8 of 10) | at least 90% | no |
| Relate | 20 of 20 paths, only 11 of 20 explanations passed the citation check | paths correct | partly |
| Router (rules only) | 92% (46 of 50) | at least 85% | yes (model step never measured) |
| Local query p95 and cost | cost about $0.0035; **p95 never measured end to end** | p95 at most 8 s, at most $0.03 | cost yes, p95 unknown |
| Retrieval load | 2 to 3 questions per second per process; p95 5.9 s at 10 at once before the model call | p95 at most 8 s | at risk |

## What is still open (carried into this phase)

- **Live answers are not wired in.** The API image does not contain the search code, and the two
  packages have conflicting pins (`neo4j` 5.28 vs 6.4, FastAPI). D43 (API imports the pipeline
  package) cannot be followed as written: it needs a change request.
- No per-request time limit, no retry with back-off for Neo4j and Qdrant, the daily cost cap and
  rate limits never exercised with a real model.
- The easy-set paid run, the router's model step, relate-explanation failures (9 of 20), and the
  optional rerank for the baseline were never done or diagnosed.
- Owner reviews still open: Phase 3 (20 community ratings, 10 judge verdicts) and Phase 4
  (30 hard questions, 20 relate pairs, 10 unanswerable questions, especially U09 and U10).
- No HTTPS, no backups, no restore test, no runbook; monitoring is logs only (D55).
- The corpus is the 25 development papers, not the 200 to 300 of the blueprint.
- Smaller items: D5 and D6 (extraction model and gleaning) never formally decided; keyboard-only
  and screen-reader checks; no automated web tests; the clarify wording was never seen on screen.

## What Phase 7 builds

| Part | What |
|---|---|
| Live answers | The screen asks a real question and gets a real answer with sources, graph and citation check, through the chosen wiring (D61) |
| Reliability | Per-request time limit, retry with back-off for the databases, a model-call circuit breaker, the cost cap and rate limits exercised live |
| Fixes | Stricter entity matching for generic words and model names (refusal), diagnose the 9 unverified relate explanations, and a measured experiment on the context size (8,000 vs 12,000 tokens) |
| Final evaluation | One run on the final system: local hard and easy sets, global set, relate pairs, unanswerable questions, router with its model step, and p95 latency over sequential live queries; results written by a script into `docs/EVALUATION.md` |
| Owner review | Review pages for what changed, plus a spot-check of 10 citations and 10 judge verdicts |
| Operations | Backup scripts for Postgres, Neo4j and Qdrant, a **tested restore**, a runbook, a one-command start, health check and troubleshooting list |
| Release | README final, architecture page, demo script (3 minutes), "how to explain it in an interview" page, known limits, tag `v1.0` |

## Not in this phase

Sign-in and accounts, PDF or image uploads (they would reopen D59), a bigger corpus (D62),
Prometheus and Grafana (D55), paid hosting unless you choose it (D60).

## Decisions (my recommendation first)

| ID | Question | Recommendation |
|---|---|---|
| D60 | What "launch" means | **Local launch**: the project runs from the README on any machine with Docker, with HTTPS in front only if you want to share it. A public internet host costs money and has not been security-reviewed by anyone but me; I would add one only if you ask, after a short extra hardening list. Option B: a small paid server for a public demo (monthly cost, needs your approval and a domain) |
| D61 | How live answers reach the screen | A **separate internal search service**: a second container built from the existing pipeline image (it already has all pins) that exposes a small internal HTTP endpoint; the API calls it. Reason: no version conflict, nothing in the API image changes, the cost cap and limits stay in the API. Not chosen: forcing both packages into one image (conflicting pins, risky), or moving the API into the pipeline image (large image, weaker isolation). This **amends D43** and needs a change request, which I will write |
| D62 | Corpus size | **Stay at 25 papers** for v1 and say so. Rough estimate for 200 to 300 papers: about 8 to 12 times the Phase 2 and 3 cost, so roughly **$30 to $40** plus days of review. An estimate, not a measurement |
| D63 | Evaluation budget | Hard cap **$3.00** for the whole phase, a shown estimate and your yes before every paid batch. My estimate: final evaluation about $1.5 to $2.0, smoke tests and the context experiment about $0.3 |
| D64 | Fix or accept the known misses | **Fix** the refusal weakness (free to develop, then checked on the unanswerable set) and **diagnose** the relate failures; **measure** the larger context once; **accept and state** F1 0.79 and any other target still missed, with the reason. No hiding of a missed target |
| D65 | Reliability and monitoring | Health check, JSON logs, backups and a tested restore; still no Prometheus or Grafana |
| D66 | Your key | You put `OPENAI_API_KEY` into the git-ignored `.env` yourself; I never see it and never print it. You set the monthly limit in the OpenAI dashboard first (a limit of $5 is enough) |

## Build steps

1. Change request for D61, then the internal search service with mocks, tests and a first live smoke test (under $0.05).
2. Time limits, retries, circuit breaker; exercise the cost cap and rate limits live with a few cheap calls.
3. Fixes from D64: entity matching for generic names, relate diagnosis, the context-size experiment.
4. Evaluation script that writes `docs/EVALUATION.md`; dry-run estimate; **your yes**; the paid run.
5. Owner review pages and the spot-check; re-run only what you change (cached).
6. Backups, restore test, runbook, one-command start.
7. Release pages, demo script, interview page, final README, CI for the new service.
8. Final A to J report, your approval, merge, tag `phase-7` and `v1.0`.

## Cost

About **$2 to $2.5** of OpenAI spend if everything goes as estimated, against a **$3.00 cap** (D63).
This month's spend so far is about $3.6 (Phases 1 to 4 plus small extras); with a $5 monthly limit
that is too tight, so a **$10 limit** is the safe setting. Everything else is free. No hosting cost
unless you choose option B of D60.

## Exit

A person can start the project from the README, ask any question and get a live cited answer or an
honest refusal; the README tables come from `docs/EVALUATION.md`; a backup can be restored; every
missed target is listed with its reason; CI is green; you approve and the tag `v1.0` is set.
