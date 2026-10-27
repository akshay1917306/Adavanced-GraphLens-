# Phase 5: Product UI and API

Source: blueprint v1.0 Part 3 (UX and UI), section 5.1, and [CR-0001](../../adr/CR-0001-simplified-dashboard.md).
Plan approved by the owner on 2026-10-26 (D42 to D48 and CR-0001 as recommended; no local model
download; fixtures instead; no push yet).

## Goal

Let a person **ask a question in a browser and see the answer with its proof**: numbered sources,
a small evidence graph, the citation-check result, and an optional side-by-side with normal RAG.
Until now everything is a command line. Phase 5 puts the Phase 1 to 4 engine behind a small API
and one screen.

## What Phase 5 builds (simple view, CR-0001)

| Part | What the user sees |
|---|---|
| Ask screen | Question box, answer with numbered source chips |
| Why this answer | Sources used and a small evidence graph (4 to 6 dots, shape by type, dashed for low confidence); selecting a dot shows its passage; a text list of the same dots and links for accessibility |
| Mode | Automatic (router); the chosen mode is shown as text; one "Compare with normal RAG" switch |
| Trust badge | "Citations checked", "Some statements not supported", or "Not checked" |
| Refuse / clarify | A plain message when the system refuses or asks which entity |
| Feedback | Thumbs up or down, stored |
| Read-only status | Index version, quality checks, last evaluation numbers (admin key, not in the demo path) |

Later view (backlog, only if time allows): full graph explorer, community tree, manual mode
chips, entity pages.

## What the API needs

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/ask` | Question in; answer, mode, citations with passages, evidence graph, check status, cost, latency out. Question length limited to 4,000 characters; same sanitiser as Phase 4 |
| `POST /api/v1/feedback` | Thumbs up/down for an answer id |
| `GET /api/v1/status` | Index version, counts, last quality checks (read-only, admin key) |
| `GET /api/v1/health` | Exists since Phase 0 |

Answers, traces and feedback go into tables that already exist (`conversations`, `messages`,
`retrieval_traces`, `answer_meta`, `feedback`), so no schema change.

## Not in this phase

Sign-in, user data, per-user rate limits, admin write actions, internet deployment (Phase 6 and
7); incremental updates (v1.5). The app runs on localhost only.

## Decisions (approved as recommended)

| ID | Question | Decision |
|---|---|---|
| D42 | UI scope | Approve CR-0001: one simple Ask screen plus Compare switch; graph explorer stays in the backlog |
| D43 | How the API reaches the search code | The API image installs the `graphlens_pipeline` package and calls it directly (one process). Not chosen: calling the command line (slow, hard to test) or a separate search service (more to run and secure) |
| D44 | Answer delivery | One JSON response first. Streaming (SSE) only if time is left |
| D45 | Evidence graph drawing | Hand-written SVG, no chart library (4 to 6 nodes), plus a text list for screen readers |
| D46 | Models while building | **No OpenAI calls** (owner's instruction) and **no local model download** (owner's choice). Tests use labelled mocks and a **fixture mode** that replays saved answers. Live answers only after the owner's explicit yes |
| D47 | Look and feel | Plain CSS with a few variables, light and dark theme, phone width; no UI kit |
| D48 | Security basics | API binds to `127.0.0.1`, CORS only for the web origin, question length cap, answers rendered as text only, no secrets in the browser bundle, errors without internals. Rate limits and users stay in Phase 6 |

## Build steps

1. API skeleton: settings, the `ask` service wrapping Phase 4, response models, error shape.
2. Persistence of answers, traces, feedback; `status` endpoint.
3. Fixture mode and mock-model tests; API tests for validation, refusal, clarify, errors.
4. Web: Ask screen, answer with source chips, trust badge, refuse/clarify messages.
5. "Why this answer" panel: passages and the small SVG evidence graph with the text alternative.
6. Compare switch, feedback buttons, theme, phone layout.
7. Checks: typecheck, lint, build, accessibility pass, real screens in the built-in browser.
8. Docs, WALKTHROUGH, README, CI, A to J report.

## Cost

$0 planned. No paid model calls. A few live answers through OpenAI (about $0.004 each) only if the
owner says yes to a named call. No new web packages planned.

## Exit

A person can open `http://localhost:3000`, ask a question, and see answer, sources, graph and
trust badge; refusal and clarify work; feedback is stored; tests, lint and CI pass; the owner approves.
