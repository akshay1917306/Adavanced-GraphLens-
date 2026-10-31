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

Tests: API 198 pass (31 new in `api/tests/test_auth.py`, on a throwaway database), pipeline unchanged,
`eslint`, `tsc`, `next build` pass. Browser check on a separate empty stack (`gltest`), not on the real data.

- [x] Threat list written before code (`THREATS.md`, `DESIGN-B.md`); owner approved the defaults (D76)
- [x] Sign up, sign in, sign out, delete account; passwords hashed with argon2id, never logged (test greps the logs for the password, codes and tokens; browser check greps the container logs: 0 hits)
- [x] Recovery codes: 8 single-use codes shown once, only hashes stored; reset works once per code (test and browser)
- [x] Owner-issued reset link: works once, expires in 30 minutes, audited (test; browser used the real script and page; the 30-minute expiry was tested by moving the clock in the database, not by waiting)
- [x] A reset ends all sessions of that account (test and browser)
- [x] Login and reset rate limits per address and per typed email; generic errors (tests; the real Redis limiter answered 429 in the browser run). **Account enumeration is NOT fully closed:** sign-up says the email exists, and the admin link route says 404
- [x] A user never sees another user's rows (tests for history, conversation, delete, feedback, saved, preferences; browser: second account got 404 for the first account's conversation); anonymous mode still works (the 167 older tests pass)
- [x] Claiming anonymous data is opt-in and one time (tests and browser)
- [ ] Cookies, CSP and headers unchanged or stricter; secret scan and dependency audit green: **local gitleaks to run before the push; CI `audit` job will check the new packages (`argon2-cffi`, `cffi`, `pycparser` pinned to 3.0 because 3.12 is under two weeks old)**
- [x] Two-account check by hand in the browser (done through the app's own page and same-origin requests; the buttons were mostly driven by script, so the look of the screens was not reviewed by a person)

## Release

- [ ] `ruff`, `pytest`, `tsc`, `eslint`, `next build` pass; CI green
- [ ] README, LIMITS, RUNBOOK, STATUS, WALKTHROUGH, DECISIONS updated
- [ ] Owner approved; tags `phase-8a`, `phase-8b`, `v1.5`
