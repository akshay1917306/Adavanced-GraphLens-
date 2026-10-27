# Phase 6 acceptance checks

Mark an item only after it was run, and say where it was run.

## Build

- [ ] Signed visitor token: forged, expired and missing tokens never reach another visitor's data
- [ ] History list, open one, delete one, delete all my data (rows really gone), save with note, preferences
- [ ] Every data route checks ownership; reading or deleting another visitor's row returns "not found"
- [ ] Rate limits per visitor and per address; 429 with `Retry-After`; counters reset
- [ ] Daily cost cap stops model calls and says so (tested with a fake model)
- [ ] Admin status writes an audit-log row; wrong or missing key is refused
- [ ] Screen: history, delete with confirmation, save, preferences, rate-limit message

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
