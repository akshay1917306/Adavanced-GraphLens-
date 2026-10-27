# Phase 5 walkthrough: API and Ask screen

## 1. What we built

A browser screen at `http://localhost:3000` where you pick or type a question and see the answer
with its proof, backed by a small API.

- **Ask screen**: question box, saved example questions, answer with numbered source chips, a
  trust badge ("Citations checked", "Some statements not supported", "Not checked"), plain
  messages for refusals, thumbs up/down, a "Compare with normal RAG" switch, light/dark theme.
- **Why this answer**: the sources used, and a small evidence graph (at most 6 dots; shape =
  entity type). Clicking a dot shows its quoted passage, or says it is not quoted. The same
  dots and links are also written as text.
- **API**: `POST /api/v1/ask`, `POST /api/v1/feedback`, `GET /api/v1/examples`,
  `GET /api/v1/status` (read-only, needs `X-Admin-Key`, off unless `ADMIN_API_KEY` is set),
  `GET /api/v1/health`.
- **Storage**: answers, cited items and ratings go into the existing tables, no schema change.

Not built: live answers from the screen, relate and global replay, sign-in, streaming, the graph
explorer (all later or backlog).

## 2. How it works

1. The browser calls only the web server (`/api/ask` and friends). The web server forwards to the
   API using `API_URL` (`web/lib/proxy.ts`).
2. The API validates the question (1 to 4,000 characters, nothing else allowed) and asks the
   engine. The engine today is **replay** (`api/app/replay.py`): five real answers and two
   refusals saved from the Phase 4 evaluation, with real passages and a graph rebuilt by the
   free `export-replay` command (`pipeline/graphlens_pipeline/replayexport.py`). An entry is kept
   only if the rebuilt context still holds every cited label and the citation check gives the
   same result. Any other question gets a plain refusal; nothing is made up.
3. The API stores the answer and returns its id; the screen uses that id for ratings. If storing
   fails the answer is still shown and ratings are switched off.
4. The screen draws the answer as text only. Chips like `[T1]` become buttons; a label that has
   no source is shown as a dashed "missing" chip.

## 3. Checks that were run

| Check | Result |
|---|---|
| API: `ruff`, 32 unit tests, 2 store tests on a temporary Postgres database | pass (Docker) |
| Pipeline: `ruff`, 3 new tests | pass (Docker) |
| Web: `next build`, `eslint`, `tsc` | pass (Docker) |
| Browser: answer, chips, badge, graph click, compare, thumbs (row appears in Postgres), refusal, dark and light, 375 px | looked right |
| Browser: fake answer with script and image tags | shown as text, nothing ran |
| Browser: API down and network down | plain messages |
| Built web files searched for keys and internal addresses | none found |
| Contrast, both themes | all pairs at least 5.0 |
| CI | not run yet |

## 4. Honest limits

- Only saved answers; replayed answers show cost and latency as 0.
- No automated web tests; browser checks were done by hand through the built-in browser.
- Full keyboard-only walk-through and screen-reader test were not done.
- Live mode needs the pipeline package inside the API image: the two have different pins
  (`neo4j` 5.28 vs 6.4, FastAPI), to be settled first.
- No sign-in: all ratings belong to one anonymous visitor. Not production-ready, not security-reviewed.

## 5. How to run

```bash
docker compose up -d --build
```

Starts postgres, neo4j, qdrant, redis, api and web. Open `http://localhost:3000`.
API docs: `http://localhost:8000/docs`.
