# Phase 6 acceptance checks

Mark an item only after it was run, and say where it was run.

## Build

- [x] Signed visitor token: forged, expired and missing tokens never reach another visitor's data
      **Result:** unit and store tests in Docker (65 pass) and a curl check against the running stack, 2026-10-27.
- [x] History list, open one, delete one, delete all my data (rows really gone), save with note, preferences
      **Result:** API only so far; 90 tests in Docker plus a curl check on the running stack, 2026-10-27. Screen not built yet.
- [x] Every data route checks ownership; reading or deleting another visitor's row returns "not found"
      **Result:** tests for all 9 data routes with a missing or forged token (401) and two-visitor store tests, plus curl.
- [x] Rate limits per visitor and per address; 429 with `Retry-After`; counters reset
      **Result:** unit tests (fake clock for the reset) and a live check with real Redis through the web server, 2026-10-27.
- [x] Daily cost cap stops model calls and says so (tested with a fake model)
      **Result:** unit test with a fake model costing 0.6 per answer and a cap of 1.0: third answer refused with `daily_limit`. Not exercised live (replay answers cost 0).
- [ ] Admin status writes an audit-log row; wrong or missing key is refused
- [x] Screen: history, delete with confirmation, save, preferences, rate-limit message
      **Result:** checked by script in the built-in browser, 2026-10-27 (see STATUS); keyboard-only walk-through not done.

## Security and quality

- [ ] Content-Security-Policy and the other headers present on web and API (checked in the browser and by test)
- [ ] Request size and time limits; no question text in logs; request id in every log line
- [ ] Abuse tests pass: other visitor's data, oversized and malformed bodies, repeated requests, forged tokens
- [ ] `npm audit` and `pip-audit` run; every finding fixed or listed with a reason
- [ ] Secret scanner in CI passes
- [ ] Load test: 1, 3 and 10 at once on replay and on the free retrieval path; median, p95, errors reported
- [ ] `ruff`, `pytest`, `tsc`, `eslint`, `next build` pass; CI green
- [ ] Real screens checked in the built-in browser, including two separate profiles

## Docs and review

- [ ] WALKTHROUGH.md, README, STATUS.md, DECISIONS.md updated
- [ ] Owner tried two browser profiles and approved Phase 6
