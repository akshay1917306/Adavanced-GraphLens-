# Phase 6: User data and hardening

Source: blueprint v1.0 section 5.1 (phase list), decisions D11 and D50, Phase 3 and 4 notes that
left rate limits, access control and the load test for this phase. The blueprint text itself is
not in the repository, so the scope below comes from those notes; where it is my reading, it is
marked as a decision for you.

## Goal

Make the app safe to hand to another person on a trusted network: every visitor sees **only their
own** history, can **delete** it, cannot flood the system, and cannot read admin data, and the
known weak spots from the phase reviews are closed or written down. It is still **not** an
internet-ready product; hosting is Phase 7 (D12).

## What Phase 6 builds

| Part | What |
|---|---|
| Visitor identity | Each browser gets an anonymous, signed visitor token (no sign-in: D11 defers it to v1.5). The API accepts only tokens it signed |
| User data | List my past questions, open one, delete one, delete all my data, save an answer with a note, keep my theme and default mode (tables already exist) |
| Access control | Deny by default; every read and write checks the visitor owns the row; admin status needs the key and writes an audit-log row |
| Rate limits | Redis counters per visitor and per address on ask and feedback; clear 429 message; a daily cost cap that stops model calls (`LLM_DAILY_COST_CAP_USD`, in the backlog since Phase 1) |
| Hardening | Security headers and a strict Content-Security-Policy on the web server, size and time limits, request ids in logs, no question text in logs, errors without internals |
| Abuse tests | Automated tests for reading someone else's conversation, oversized and malformed input, repeated requests, forged tokens |
| Dependency and secret checks | `npm audit`, a Python dependency audit, a secret scanner in CI |
| Load test | 3 and 10 requests at once through the API (replay answers) and through the free retrieval path (no model call), with the timings reported |

## Not in this phase

Sign-in or accounts (v1.5), hosting, HTTPS and a domain (Phase 7), live model answers from the
screen (Phase 7 with your OpenAI key, see D58), Prometheus or Grafana (D55), incremental
updates (v1.5), a bigger corpus.

## Decisions (my recommendation first)

| ID | Question | Recommendation |
|---|---|---|
| D51 | Visitor identity | The web server asks the API for a **signed visitor token** (random id plus HMAC, secret in `.env`), stores it in an `HttpOnly`, `SameSite=Lax` cookie, and forwards it to the API. A forged or missing token gets a new visitor, never someone else's data. Not chosen: trusting a plain id from the browser (anyone could guess or copy it) |
| D52 | User-data scope | History list, open, delete one, delete all, save with note, preferences. Deleting is real deletion of the visitor's rows (conversations cascade), not just a hidden flag. Sharing links (`share_token`) stay off |
| D53 | Rate limits | Redis, fixed window: 10 asks per minute and 100 per day per visitor, 30 asks per minute per address, 60 feedback per minute per visitor. Numbers are settings, not code. Over the limit: HTTP 429 with a plain message and `Retry-After` |
| D54 | Web hardening | Content-Security-Policy with no inline script, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options: DENY`, `Permissions-Policy`; same simple headers on the API. May need small code changes (Next inline scripts) |
| D55 | Monitoring | Structured JSON logs with request id, route, status and timing; **no** Prometheus, Grafana or OpenTelemetry now. Reason: a large extra stack for a local-only app; revisit at launch. Phase 0 listed them for Phase 6, so this is a change you should confirm |
| D56 | Security checks | `npm audit` and `pip-audit` (a small install in a throwaway container), gitleaks in CI, and the abuse tests above. Findings are fixed or listed with a reason; I do not claim "secure", only what was checked |
| D57 | Load test | Replay answers and the free retrieval path only (no model call, no cost): 1, 3 and 10 at once, report median and p95 and any error. A load test of paid model calls is not run |
| D58 | Live answers | Not in Phase 6. Wiring the search code into the API needs the package version conflict settled and your OpenAI key, so it opens Phase 7 |

## Build steps

1. Visitor token: API endpoint to issue and verify, web cookie handling, tests with forged and expired tokens.
2. Ownership checks on every data route; migrate the single `local-demo` visitor's rows (keep or delete: your choice, see prerequisites).
3. History, delete one, delete all, saved answers, preferences: API and tests (including reading another visitor's data).
4. Screen: history list, delete buttons with confirmation, save with note, preferences.
5. Rate limits and the daily cost cap, with tests and a clear screen message.
6. Security headers, limits, request ids, log hygiene; admin audit log.
7. Dependency audits, secret scanner in CI, abuse test suite.
8. Load test and timings.
9. Docs, WALKTHROUGH, README, CI, A to J report.

## Cost

$0. No OpenAI calls. A throwaway container installs `pip-audit` (a few MB) and gitleaks runs in
CI only; I will ask before any download.

## Exit

A second browser profile cannot see or change the first one's history; limits trigger and reset;
deleting works and leaves no rows; headers and tests pass; audits are reported with their
findings; CI is green; you approve.
