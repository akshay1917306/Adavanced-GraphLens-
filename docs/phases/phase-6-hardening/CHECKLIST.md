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
- [x] Admin status writes an audit-log row; wrong or missing key is refused
      **Result:** unit tests and a store test on a temporary Postgres; not tried on the running API (the status page is off without a key).
- [x] Screen: history, delete with confirmation, save, preferences, rate-limit message
      **Result:** checked by script in the built-in browser, 2026-10-27 (see STATUS); keyboard-only walk-through not done.

## Security and quality

- [x] Content-Security-Policy and the other headers present on web and API (checked in the browser and by test)
      **Result:** curl on the running stack, API tests, and the browser (no violations; three attacks blocked).
- [x] Request size and time limits; no question text in logs; request id in every log line
      **Result:** size limit 32 KB (411 and 413) and log-content tests pass. A time limit per request was not added (replay answers are instant; add it with live answers in Phase 7).
- [x] Abuse tests pass: other visitor's data, oversized and malformed bodies, repeated requests, forged tokens
      **Result:** in the 123 API tests (`test_visitor`, `test_userdata_*`, `test_hardening`, `test_ratelimit`, `test_storage_errors`), including broken JSON, form bodies and hostile ids.
- [x] `npm audit` and `pip-audit` run; every finding fixed or listed with a reason
      **Result:** web 0, API 0; pipeline pypdf and pillow listed with reasons in `AUDIT.md` (accepted risk D59, confirmed by the owner).
- [x] Secret scanner in CI passes
      **Result:** gitleaks passes locally on 87 commits (negative check catches a real-looking key); the CI job is committed but has not run on GitHub yet.
- [x] Load test: 1, 3 and 10 at once on replay and on the free retrieval path; median, p95, errors reported
      **Result:** `LOAD_TEST.md`. Replay: 0 errors, p95 at most 226 ms. Retrieval: 0 failures, p95 1.3 s at 3 and 5.9 s at 10 at once; scaling limit noted.
- [ ] `ruff`, `pytest`, `tsc`, `eslint`, `next build` pass; CI green
      Partly: all pass in Docker (123 API tests, 400 pipeline tests); **CI has not run on GitHub for this branch**, including the new `secrets` and `audit` jobs.
- [x] Real screens checked in the built-in browser, including two separate profiles
      **Result:** two identities (`localhost` and `127.0.0.1`): no access in either direction (404), settings and delete-all stay separate. Keyboard-only walk-through not done.

## Docs and review

- [x] WALKTHROUGH.md, README, STATUS.md, DECISIONS.md updated
- [ ] Owner tried two browser profiles and approved Phase 6
