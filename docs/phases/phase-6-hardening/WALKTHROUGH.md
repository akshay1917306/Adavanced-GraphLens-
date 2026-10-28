# Phase 6 walkthrough: user data and hardening

## 1. What we built

The app is now safe to hand to another person **on a trusted network**: each visitor has private
data they can delete, the system cannot be flooded, admin data is closed by default, and the weak
spots found in the reviews are closed or written down. It is still **not** an internet-ready
product (no HTTPS, no hosting, no backups: Phase 7).

| Part | What it does |
|---|---|
| Visitor identity | No sign-in (D11). The API gives each browser a **signed token** (`v1.<id>.<expiry>.<HMAC>`); the web server keeps it in an `HttpOnly`, `SameSite=Lax` cookie the page's JavaScript cannot read. A forged, expired or unknown token gets a fresh visitor, never someone else's data |
| User data | My questions (with "Ask again"), delete one, saved answers with a note, settings (theme, "Why this answer" open by default), **delete all my data** (the visitor and every row under them are removed for real) |
| Access control | Every query is limited to the visitor's own rows; a row that belongs to someone else answers "not found", the same as a row that does not exist. Admin status needs a key, is off when none is set, and writes an audit row for every view and every refused key |
| Limits | Redis fixed windows: 10 asks per minute and 100 per day per visitor, 30 asks per minute per address, 120 other requests per minute, 10 new visitors per minute per address, 10 admin-key guesses per minute. 429 with `Retry-After`. A daily cost cap stops paid answers. If Redis is down, requests are refused |
| Hardening | Request id on every response; `nosniff`, no-referrer, no-store, frame deny; a strict Content-Security-Policy (a fresh nonce per page on the web server); 32 KB body limit (411 and 413); JSON logs with no question, token, key or query string; database outage gives a retryable 503; React error pages that never print the error text |
| Checks | Dependency audits, a secret scan of files and history, a load test, an error catalogue ([ERROR_HANDLING.md](../../ERROR_HANDLING.md)) |

Not built: sign-in, hosting and HTTPS, backups, monitoring dashboards (D55), live model answers
(Phase 7), the full-text history with passages (the schema has no place to keep them).

## 2. How a request flows now

1. The browser calls only the web server (`/api/...`). It has no token in JavaScript.
2. The web server reads the cookie. With no cookie it asks the API for a new visitor token; with a
   rejected token (401) it asks for a fresh one and tries once more. It forwards the client address
   together with a shared secret so the API can trust it for limits.
3. The API middleware adds the request id, refuses oversized or length-less bodies, and later adds
   the security headers and writes one log line (request id, method, route template, status, time).
4. A route dependency checks the signed token, then the limits (visitor, address, daily cost), then
   the route runs a query that always includes the visitor id.
5. Errors leave as `{"error": {"code", "message"}}` with a stable code; the page shows a plain
   message. See the catalogue for every code and what the screen does with it.

## 3. Checks that were run

| Check | Result |
|---|---|
| API: `ruff`, 123 tests (token, ownership with two visitors on a temporary Postgres, limits with a fake clock and fake Redis, cost cap with a fake paid model, headers, logs, audit, body limits, broken JSON, hostile ids, database down) | pass (Docker) |
| Pipeline: 400 tests | pass (Docker) |
| Web: `next build`, `eslint`, `tsc` | pass (Docker) |
| Two separate browser identities (`localhost` and `127.0.0.1` have separate cookie jars): B cannot open, delete, rate or save A's rows (all 404), B's settings do not change A's, and A's "delete all" leaves B's data | pass (built-in browser) |
| Content-Security-Policy in the browser | no violations; inline handler, other-site frame and other-origin request blocked |
| Rate limits and `Retry-After` on the running stack with real Redis | 11th ask and 10th new visitor in a minute get 429 |
| Database stopped and restarted | 503 with `Retry-After`, then 200 |
| `npm audit`, `pip-audit`, `gitleaks` | web 0, API 0, pipeline 49 accepted advisories (D59), no secret in 87 commits (see [AUDIT.md](AUDIT.md)) |
| Load test | no errors up to 10 at once; retrieval does not scale with threads (see [LOAD_TEST.md](LOAD_TEST.md)) |
| CI on GitHub | **not run yet** (two new jobs, `secrets` and `audit`, have never run there) |

## 4. Honest limits

- Anonymous only: clearing cookies or using another browser means a new visitor and no history.
- A visitor id in a stolen cookie works until it expires (one year) or the visitor deletes their data.
- No HTTPS, so the cookie has no `Secure` flag yet (set `COOKIE_SECURE=1` behind HTTPS).
- The history keeps the question and the answer text, not the passages or the graph.
- Replay answers only; the daily cost cap and per-request time limit were never exercised with a
  real model.
- Retrieval throughput is about 2 to 3 questions per second per process.
- Pipeline dependencies `pypdf` 6.19.0 and `pillow` 12.3.0 have known advisories that are accepted
  for now (D59). Nothing here has been security-reviewed by anyone else; do not expose it to the
  internet.
- No automated web tests; keyboard-only and screen-reader checks of the new tabs were not done.
- Limits and the cost cap can be changed through environment variables (`RATE_ASK_PER_MIN`,
  `RATE_ASK_IP_PER_MIN`, `RATE_GENERAL_PER_MIN`, `RATE_VISITOR_IP_PER_MIN`, `RATE_ASK_PER_DAY`,
  `LLM_DAILY_COST_CAP_USD`).

## 5. How to run

```bash
docker compose up -d --build
```

Open `http://localhost:3000`. Secrets for the visitor token, the address trust and the admin key
live in the git-ignored `.env` (`VISITOR_TOKEN_SECRET`, `PROXY_SECRET`, `ADMIN_API_KEY`); copy the
names from `.env.example` and use long random values.
