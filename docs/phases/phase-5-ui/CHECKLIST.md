# Phase 5 acceptance checks

Mark an item only after it was run, and say where it was run.

## Build

- [ ] `POST /api/v1/ask` returns answer, mode, citations with passages, evidence graph, check status, cost, latency
- [ ] Question over 4,000 characters, empty question and wrong types are rejected with a clear error
- [ ] Refusal and clarify show as plain messages, not errors
- [ ] Answers, traces and feedback are stored in the existing tables (no schema change)
- [ ] `GET /api/v1/status` is read-only and needs the admin key
- [ ] Fixture mode works with no model and no key
- [ ] Ask screen: question, answer, source chips, trust badge
- [ ] "Why this answer": passages and the small evidence graph; selecting a dot shows its passage
- [ ] Text alternative lists the same dots and links
- [ ] Compare switch shows both answers side by side
- [ ] Thumbs up/down stored
- [ ] Light and dark theme; works at 375 px width

## Security and quality

- [ ] API listens on 127.0.0.1; CORS limited to the web origin
- [ ] Answer text is rendered as text only (a test with `<script>` in an answer)
- [ ] No key or secret in the web bundle (searched)
- [ ] Errors carry no stack trace or internal names
- [ ] Keyboard use works; contrast checked; every control has a label
- [ ] `ruff`, `pytest`, `tsc`, `eslint`, `next build` pass; CI green
- [ ] Real screens checked in the built-in browser

## Docs and review

- [ ] WALKTHROUGH.md, README, STATUS.md, DECISIONS.md updated
- [ ] Owner clicked through the screens
