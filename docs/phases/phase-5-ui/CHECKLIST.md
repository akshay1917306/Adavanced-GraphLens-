# Phase 5 acceptance checks

Mark an item only after it was run, and say where it was run.

## Build

- [x] `POST /api/v1/ask` returns answer, mode, citations with passages, evidence graph, check status, cost, latency
      **Result:** checked in the browser against replay mode (cost and latency are 0 in replay).
- [x] Question over 4,000 characters, empty question and wrong types are rejected with a clear error
      **Result:** unit tests (API, in Docker); the input is never echoed back.
- [x] Refusal and clarify show as plain messages, not errors
      **Result:** refusal checked in the browser (France question); clarify has no saved example, so the clarify wording is untested on screen.
- [x] Answers, traces and feedback are stored in the existing tables (no schema change)
      **Result:** integration test on a temporary Postgres database (answer, metadata, trace, one rating per visitor).
- [x] `GET /api/v1/status` is read-only and needs the admin key
      **Result:** unit tests for the key checks; the run and quality SQL is not yet tried on real data.
- [x] Fixture mode works with no model and no key
      **Result:** replay of 5 real answers and 2 refusals; 32 API tests pass in Docker.
- [x] Ask screen: question, answer, source chips, trust badge
      **Result:** checked in the built-in browser (desktop and 375 px): question box, examples, answer, source chips, badge.
- [x] "Why this answer": passages and the small evidence graph; selecting a dot shows its passage
      **Result:** checked in the browser: clicking a dot shows its quoted passage or says it is not quoted.
- [x] Text alternative lists the same dots and links
      **Result:** checked in the browser: a text list of every link plus the item list under the graph.
- [x] Compare switch shows both answers side by side
      **Result:** checked in the browser: GraphLens and Normal RAG side by side.
- [x] Thumbs up/down stored
      **Result:** checked in the browser and in Postgres (a rating row appeared); the pressed state resets for a new answer.
- [x] Light and dark theme; works at 375 px width
      **Result:** checked in the browser: dark (system), light (emulated), 375 px width with no sideways scroll. The manual theme button was not clicked.

## Security and quality

- [x] API listens on 127.0.0.1; CORS limited to the web origin
      **Result:** Docker publishes ports 8000 and 3000 on 127.0.0.1 only (compose); CORS test passes (only the web origin is allowed).
- [x] Answer text is rendered as text only (a test with `<script>` in an answer)
      **Result:** checked by hand in the browser with a fake answer holding script and image tags: no element created, nothing executed. No automated web test exists.
- [x] No key or secret in the web bundle (searched)
      **Result:** searched the built static files in the image: no key pattern, no OPENAI, NEO4J, POSTGRES, ADMIN_API_KEY or API address; the web container only has API_URL.
- [x] Errors carry no stack trace or internal names
      **Result:** API unit tests (500 and rejected input); the screen shows only plain messages for API down and network down (checked in the browser).
- [x] Keyboard use works; contrast checked; every control has a label
      **Result:** contrast ratios computed for both themes: all text pairs at least 5.0 (AA needs 4.5); every control has a label; graph dots are focusable buttons. A full keyboard walk-through by hand was not done.
- [x] `ruff`, `pytest`, `tsc`, `eslint`, `next build` pass; CI green
      **Result:** passed in Docker, and all 4 CI jobs (pipeline, api, web, compose) passed on PR #7.
- [x] Real screens checked in the built-in browser
      **Result:** done on 2026-10-27 (desktop dark, mobile light); two fixes came from it (stale rating state, overlapping graph labels).

## Docs and review

- [x] WALKTHROUGH.md, README, STATUS.md, DECISIONS.md updated
- [x] Owner clicked through the screens and approved Phase 5 (2026-10-27)
