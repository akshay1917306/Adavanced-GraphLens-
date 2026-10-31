# Known limits

Written plainly so nobody has to discover them. Updated at the end of Phase 7.

## Quality and evidence

- **Three evaluation targets are missed**: local correctness 70% (target 75%), gap over plain RAG
  +13.3 points (target +15), p95 time 10.3 s (target 8 s). See [EVALUATION.md](EVALUATION.md).
- Only **25 development papers**. Nothing here says how it behaves on 300 papers or other subjects.
- Questions, gold answers and labels were **drafted by Claude**; the owner review of the hard set,
  the relate pairs, the unanswerable set and the Phase 3 community ratings is **still open**.
- The **judge is the same model family** as the answerer. Sets have 30 questions (10 for global), so
  intervals are wide (hard set: 52 to 83%).
- Refusal: 10 of 10 on the development set is **tuned** on that set; on 10 fresh probes it is 9 of 10
  (F03 still gets an invented answer).
- Global search results were **not re-run** in Phase 7 (carried over from Phase 3); its answers are 3.4
  times longer than the baseline's.
- Relate: 14 of 20 explanations pass the citation check; nobody has read them for faithfulness.
- Entity resolution F1 is 0.79 (target 0.85); relation precision 0.81. The graph has errors.
- The citation check proves a cited passage supports a claim according to a model, not that the claim
  is the best answer. Text cleaning of PDFs is heuristic.
- Retrieval does about 2 to 3 questions per second per process; ten users at once are slower.

## Security and operations

- Accounts are optional (Phase 8B). Anonymous visitors still work: a stolen anonymous cookie works until it
  expires or the data is deleted. A stolen session cookie works until the session is ended (30 days idle, 90
  days at most). Over plain `http` (the local default) a password and a cookie can be read by anyone on the
  same network; there is **no HTTPS**. The email is **not verified** and nothing is sent to it. A user who
  loses both the password and the 8 recovery codes depends on the owner, who can issue a one-time link
  (`scripts/reset-link.sh`). There is no second factor and no outside security review: the sign-in is built
  with the measures in docs/phases/phase-8-v1-5/THREATS.md and is not called secure. Sign-up shows that an
  email already exists. Backups hold password hashes and emails and are not encrypted.
- **No HTTPS, no monitoring, no alerts.** Do not expose it to the internet. No outside security review.
- Backups are manual; Neo4j Community can only be dumped while stopped, so the site goes down for about
  a minute. Restore was tested only into an empty stack. Redis counters are not saved.
- `pypdf` 6.19.0 and `pillow` 12.3.0 have known advisories, **accepted** (D59) because the parser runs
  only in the command-line pipeline on 25 fixed papers; upgrade and re-baseline before accepting uploads.
- `uvicorn` is not declared in the pipeline lock file (it arrives through Prefect).
- Retry on read errors covers local search and global selection, not relate path search or plain-RAG
  retrieval. A real database outage and a real timeout were not provoked live.
- The OpenAI monthly limit is the owner's setting; the code cannot verify it. The in-app daily cap
  (`LLM_DAILY_COST_CAP_USD`) and rate limits were exercised live once.
- Test conversations and visitors from the live tests remain in the local database.

## Not built

Sign-in, uploads, streaming answers, HTTPS, scheduled backups, relate/global replay answers, a larger
corpus, a reranker.
