# Phase 8 acceptance checks

Mark an item only after it was run, and say where. A missed target is reported, not hidden.

## Part A: faster and better answers

- [ ] A1 streaming: first words visible in under 2 s on a local question (measured); the final answer equals the non-streamed one; errors mid-stream shown cleanly
      **Built and tested with fakes** (pipeline 481 tests, API 167, lint, types, build, replay path in the browser). **Not yet measured with a real model:** needs a live check (about $0.01) after the owner's yes.
- [ ] A2 shorter limit: correctness, citation support, refusal and p95 measured against Phase 7 on the same questions
- [ ] A3 passage choice: same comparison; any download approved first
- [ ] A4 retry on relate and plain-RAG reads; `uvicorn` declared; tests with fakes
- [ ] Each variant kept or dropped with numbers written down; easy set and refusal set not worse
- [ ] Hard-set correctness, gap and p95 reported against 75%, +15 and 8 s (met or still missed)
- [ ] Part A spend within $0.60

## Part B: sign-in with password reset

- [ ] Threat list written before code
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
