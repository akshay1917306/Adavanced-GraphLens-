# Phase 8 acceptance checks

Mark an item only after it was run, and say where. A missed target is reported, not hidden.

## Part A: faster and better answers

- [x] A1 streaming (merged, `phase-8a`): errors mid-stream shown cleanly; tested with fakes. **The "first words under 2 s" target was MISSED**: live check of 3 questions showed the first draft word after 4.4 to 7.3 s (routing and retrieval run first), the final answer after 7.0 to 9.4 s. The draft card with a real stream was not seen in the browser.
- [x] A2 shorter limit (tried, DROPPED by the owner, D74; speed rule missed): correctness, citation support, refusal and p95 measured against Phase 7 on the same questions
- [x] A3 passage choice (variant 5 built and measured; owner keep decision pending, D75): same comparison; any download approved first
- [x] A4 retry on relate and plain-RAG reads; `uvicorn` declared; tests with fakes
- [x] Each variant kept or dropped with numbers written down (STATUS.md); **the easy set and the refusal set were NOT re-run for A3** (only the hard set), so "not worse" is unproven
- [x] Hard-set correctness 23 of 30 (76.7%, within noise); the gap and p95 were **not re-measured** in Phase 8, so +13.3 and 10.3 s from Phase 7 still stand as missed
- [x] Part A spend within $0.60 (about $0.24, estimated)

## Part B: sign-in with password reset

- [x] Threat list written before code (`THREATS.md`, `DESIGN-B.md`); owner review pending
- [ ] Sign up, sign in, sign out, delete account; passwords hashed with argon2id, never logged
- [ ] Recovery codes: 8 single-use codes shown once, only hashes stored; reset works once per code
- [ ] Owner-issued reset link: works once, expires in 30 minutes, audited
- [ ] A reset ends all sessions of that account
- [ ] Login and reset rate limits per address and per account; generic errors; no account enumeration (tested)
- [ ] A user never sees another user's rows (tests for every route); anonymous mode still works
- [ ] Claiming anonymous data is opt-in and one time
- [ ] Cookies, CSP and headers unchanged or stricter; secret scan and dependency audit green
- [ ] Two-account check by hand in the browser

## Release

- [ ] `ruff`, `pytest`, `tsc`, `eslint`, `next build` pass; CI green
- [ ] README, LIMITS, RUNBOOK, STATUS, WALKTHROUGH, DECISIONS updated
- [ ] Owner approved; tags `phase-8a`, `phase-8b`, `v1.5`
