# Phase 6 status

Last updated: 2026-10-28

## State

**Plan approved by the owner on 2026-10-27; build in progress (all build steps and docs done; waiting for CI and the owner's review and approval).** Branch
`phase-6/hardening` from `main` at 0593c11 (Phase 5 tagged `phase-5`). Nothing pushed.

## Completed

- Phase 5 checkpoint: PR #7 and the docs PR #8 merged, CI green, tag `phase-5`.

## Built so far

- The Phase 5 test rows of the `local-demo` visitor were deleted (owner's choice): 1 visitor,
  9 conversations, 3 ratings. Rows made later by the Phase 6 checks below are also test rows.
- Step 1: signed visitor token (`api/app/visitor.py`), `POST /api/v1/visitor`, ask and feedback
  need a valid token (deny by default), feedback checks that the answer belongs to the visitor,
  the web proxy keeps the token in an `HttpOnly`, `SameSite=Lax` cookie and renews it when it is
  missing, forged or unknown, and only accepts JSON posts. `VISITOR_TOKEN_SECRET` was generated into
  the git-ignored `.env`; `.env.example` has a placeholder.
- Checked: 65 API tests pass in Docker (token round trip, tampered, wrong secret, expired, wrong
  visitor, forged cookie, store-level ownership on a temporary Postgres), ruff clean, eslint and
  tsc clean. By hand with curl against the running stack: a second visitor gets "No such answer"
  for the first visitor's answer, the owner can rate it, a forged cookie is replaced by a new
  visitor, non-JSON posts and direct API calls without a token are refused; the cookie is not
  readable from page JavaScript; the screen still works.
- Step 2 (API only; the screen comes in step 4): `GET /api/v1/history`, `GET` and `DELETE
  /api/v1/history/{id}`, `DELETE /api/v1/me` (deletes the visitor and everything under them, returns
  the counts), `GET`, `POST` and `DELETE /api/v1/saved`, `GET` and `PUT /api/v1/preferences`.
  Every query is limited to the visitor's own rows and returns "not found" for anything else;
  every route refuses a missing or forged token. History shows question, answer text, mode, check
  status and rating; the passages and graph are not stored (no schema change), so an old answer
  cannot be re-opened with its sources.
- Checked: 90 API tests pass in Docker (two-visitor tests on a temporary Postgres: privacy of
  history, saved answers and preferences, hard delete of one conversation and of everything,
  other visitor untouched), ruff clean. By hand with curl on the running stack: the second visitor
  cannot open, delete or save the first visitor's rows; delete-all removes the visitor and the old
  token stops working.
- Test rows from these curl checks (a few visitors and conversations) are in the local database;
  they are cleaned at the end of the phase.
- Step 5: rate limits in Redis (`api/app/ratelimit.py`, D53): 10 asks per minute and 100 per day
  per visitor, 30 asks per minute per address, 120 requests per minute per visitor on every other
  route, 10 new visitors per minute per address; HTTP 429 with `Retry-After`. If Redis is down the
  request is refused (503), not waved through. Daily cost cap (`LLM_DAILY_COST_CAP_USD`, default 1.0):
  the cost of every answer is added to a Redis counter and answers stop at the cap. The client
  address reaches the API from the web server only together with a shared secret (`PROXY_SECRET`,
  in `.env`), so a direct caller cannot pick its own address. The web proxy passes 429 and
  `Retry-After` on to the browser; `AskApp` already shows the API's message.
- Checked: 101 API tests pass in Docker (limit counting, per-key separation, window reset by a
  fake clock, Redis down, cost cap with a fake paid model costing 0.6 per answer, all routes, the
  address rule), ruff, eslint and tsc clean. By hand on the running stack with real Redis: the 11th
  ask in a minute gets 429 with `Retry-After`; the 10th new visitor from one address in a minute
  gets 429; a direct API caller with a wrong secret cannot dodge the address limit. The limit
  reset after one minute was tested only with the fake clock, not waited out live.
- Not yet: the 100-per-day limit and the cost cap were tested with fake counters, not live; the
  screen message for 429 was not looked at in the browser.
- Step 4 (screen): tabs Ask, My questions, Saved, Settings. My questions lists past questions with
  "Ask again" (re-runs the full question) and Delete with an inline confirmation; Save under an
  answer; Saved with an editable note and Remove; Settings with theme, "Why this answer" open by
  default, and "Delete all my data" (confirmation, then the counts removed). New web routes
  forward history, saved, preferences and delete-all; ids are checked as UUIDs before they reach
  an API path; cross-site non-GET requests are refused (`Sec-Fetch-Site`).
- Checked: web `next build`, eslint and tsc pass in Docker. In the built-in browser, driven by
  script: ask, save, history list, delete shows a confirmation and Cancel keeps the row, Yes
  deletes it, Ask again returns to the Ask tab with the full question, saved note persists, theme
  and panel preferences are stored on the server and still apply after a reload, delete-all removed
  10 questions and 1 saved answer and the next visit starts clean, the 429 message appears in the
  red notice, no sideways scroll at 375 px on all four tabs.
- Not done: keyboard-only walk-through of the new tabs; screenshots of every new tab were not
  reviewed one by one (the Ask tab with the 429 message was); `default_mode` is stored but has no
  control (modes stay automatic, CR-0001); no automated web tests.
- Step 6 (hardening): API middleware (`api/app/hardening.py`) adds a request id (a sane one from
  the caller is kept, anything else replaced), `X-Content-Type-Options`, `Referrer-Policy`,
  `Cache-Control: no-store`, `X-Frame-Options` and a strict CSP (not on `/docs`), refuses POST and
  PUT without `Content-Length` (411) or over 32 KB (413), and writes one JSON log line per request
  with request id, method, route template, status and milliseconds only; uvicorn's own access log
  (which prints URLs) is switched off. Admin status writes an `admin_audit_log` row for every view
  and every refused key, and guessing is limited to 10 per minute per address. Web: `proxy.ts`
  sets a CSP with a fresh nonce on every request (the page is rendered per request), `next.config.ts`
  sets the fixed headers and `no-store` on `/api/*`. `upgrade-insecure-requests` is left out until
  HTTPS (Phase 7).
- Checked: 113 API tests pass in Docker (headers on success and error, request id handling, 411,
  413, logs contain no marker text from body, query string or token, unexpected error logged by
  type and request id only, audit rows, admin guess limit, audit row on a temporary Postgres), ruff
  clean, web build, eslint and tsc pass. On the running stack by curl: headers on page, `/api/*`
  and API; 411 and 413; request-id log lines. In the browser: the app works under the CSP with no
  violations and all 10 scripts carry the nonce; an inline `onerror` handler, an iframe to another
  site and a fetch to another origin were each blocked and reported. A script added from devtools
  ran (strict-dynamic trusts scripts created by trusted code), so that test proves nothing.
- Not checked: the audit log against the running API (no `ADMIN_API_KEY` is set, so the status
  page is off there); `style-src` has no `unsafe-inline`, no violation was seen, but not every
  state of every tab was exercised under it; 429 responses to the page's own calls appear in the
  console when many test requests were sent in one minute.
- Error-handling catalogue: `docs/ERROR_HANDLING.md`. Two of its gaps were fixed: a database that is
  down now gives 503 `storage_unavailable` with `Retry-After` (connect timeout 3 s; 118 API tests
  pass; live: Postgres stopped, 503, started, 200), and the web app has `error.tsx` and
  `global-error.tsx` (a plain message and "Try again"; checked in the browser with a temporary
  crashing page that was deleted again; `global-error.tsx` was not triggered).
- Step 7 (audits and secret scan; details in `AUDIT.md`): `npm audit` 0 vulnerabilities; API
  `pip-audit` none; pipeline `pip-audit` found `pypdf` 6.19.0 (11) and `pillow` 12.3.0 (38). pypdf
  6.21.2 passes all 400 pipeline tests but changes the extracted text of all 25 corpus PDFs
  (whitespace only in the 3 compared), which would force paid re-extraction, and pillow is capped
  by `fastembed`, so both stay pinned as an accepted risk (D59, confirmed by the owner on 2026-10-28). I
  tried the upgrade and reverted it, so `uv.lock` is unchanged. Gitleaks scanned 87 commits: no
  real secret, `.env` never committed; one made-up test token is allowlisted by its exact value, and a
  negative check shows a real-looking key is still caught. CI got two jobs: `secrets` (gitleaks)
  and `audit` (npm and API). Neither CI job has run on GitHub yet.
- Step 8 (load test; details in `LOAD_TEST.md`): replay asks straight at the API and through the
  web server, 60 requests per level from 10 visitors: 0 errors at 1, 3 and 10 at once, p95 at most
  226 ms. Retrieval path of local search with the real databases and no model call: 0 failures, but
  throughput stays at about 2 to 3 questions per second, so median 0.5 s (1 at once), 1.1 s (3) and
  4.7 s (10, p95 5.9 s); 10 at once would miss the p95 under 8 s target once a model call is added.
  The rate limits were raised for the run through environment variables and restored afterwards
  (checked: 10 per minute per visitor and 30 per address are back). Not covered: a real model call,
  the API process itself for retrieval, long runs, global search, relate mode.
- Step 9: two-profile check in the browser (see CHECKLIST), 5 more abuse tests (123 API tests
  pass), the local database cleaned of all test rows (43 visitors, 389 conversations from today's
  checks and load test; the corpus tables are unchanged: 35 documents, 751 text units, 3,173 cache
  rows; about 33 Redis limit counters remain and expire by themselves), WALKTHROUGH, README and
  DECISIONS updated.
- Downloads made with the owner's yes: `pip-audit` (in a throwaway container) and the
  `ghcr.io/gitleaks/gitleaks:v8.21.2` image.
- Many test rows (visitors, conversations) exist in the local database after these checks;
  they are cleaned at the end of the phase.

## Blockers

None.

## Decisions waiting for the owner

- D51 to D58 in `BRIEF.md` (D55 and D58 change earlier notes: no Prometheus or Grafana, live
  answers wait for Phase 7).
- What to do with the Phase 5 test rows of the `local-demo` visitor.

## Exact next action

Owner reviews and approves; then push `phase-6/hardening`, open the PR, watch CI (including the new `secrets` and `audit` jobs, which have never run), merge, tag `phase-6`. Nothing is pushed yet.
