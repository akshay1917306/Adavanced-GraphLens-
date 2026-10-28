# Errors in GraphLens and how each one is handled

This page lists the errors the project can produce, layer by layer, what the code does about each
one **today**, and what is still missing. It is written from the code (Phases 0 to 6, state on
2026-10-28), not from a plan. Status marks:

- **Done**: the code handles it and a test or a manual check ran.
- **Partly**: handled, but with a stated gap.
- **Gap**: not handled well yet; a proposal is given.

## 1. Rules used everywhere

| Rule | Meaning |
|---|---|
| Four kinds of error | **Bad input** (the caller can fix it: 4xx), **refusal** (the system declines on purpose: not an error), **system fault** (we or a dependency broke: 5xx), **attack** (looks like abuse: refused quietly) |
| Deny by default | When a security check cannot be completed (no secret, Redis down, token unknown) the request is refused, never waved through |
| Never invent | If evidence is missing the system refuses or says "not checked". It does not guess an answer |
| Never leak | A person sees a short plain message with a stable `code`. Stack traces, SQL, file paths, keys, tokens and the person's own text are not sent back or logged |
| Retry only what is safe | A retry is allowed for model calls (at most 2 by the client, at most 3 tries when the answer shape is wrong) because results are cached by hash and cost is capped. Writes to the database are not retried blindly |
| Bound the cost | Every paid batch has a cap; reaching it stops new calls and says so. Spent money is still counted |
| Fail one item, not the run | One bad file, unit, batch or pair is recorded with a reason and the rest continues; a re-run resumes from the cache |
| Log by type | Logs carry error type and request id only |

## 2. Preparing the data (ingest, Phase 1)

| Error | Cause | What happens | Status |
|---|---|---|---|
| `IngestError` file missing, empty, not a PDF, encrypted, more pages than the limit, larger than the size limit | Bad or hostile file | That file is skipped, the reason is recorded, other files continue | Done |
| `IngestError` hash mismatch | File changed after download (tampering or corruption) | File refused: content hash is the identity of a document | Done |
| `IngestError` license missing or not plain CC BY | Policy | File refused, not ingested | Done |
| `IngestError` no extractable text (scanned) or no text left after cleaning | Image-only PDF | Skipped with reason; no OCR is attempted | Done (OCR is out of scope) |
| Unexpected exception while reading a PDF | Parser bug | Caught per file, only the exception type is reported | Done |
| Network drop while downloading or installing | Flaky internet | Retry loops in the Dockerfile and download script; finished work is cached, so run again | Partly (manual re-run) |

## 3. Extraction with the model (Phase 2)

| Error | Cause | What happens | Status |
|---|---|---|---|
| `OPENAI_API_KEY` or model name not set (`LlmError`) | Missing or placeholder `.env` | Command stops before any call with a clear message (exit code 2) | Done |
| Timeout or connection error | Network or provider | Client retries twice, then `LlmError`; the unit is recorded as failed, other units go on; re-run continues from `extraction_cache` | Done |
| Answer is not valid JSON, wrong shape, or cut off at the output limit | Model behaviour | Asked again up to 3 times, then `ExtractionFailed` for that unit | Done |
| Entity or relation breaks the ontology (wrong type or predicate) | Model behaviour | The item is dropped and counted by reason in the report (not stored) | Done |
| Cost cap reached | Budget | No new calls start; the report says how many units were left | Done |
| Model has no known price while a cap is set | New model name | Refused rather than spending without a count | Done |
| Local model server used (`LLM_BASE_URL`) | Optional | Cost counts as 0; time limit is 4 times longer | Done (never run live) |

## 4. Resolution, graph load, communities (Phases 2 and 3)

| Error | Cause | What happens | Status |
|---|---|---|---|
| Judge answer not usable | Model | The pair stays **separate** (the safe side: a missed merge is better than a wrong one) | Done |
| Cost cap reached in resolution | Budget | Remaining gray-zone pairs stay separate and are counted (`unasked_pairs`) | Done |
| Wrong merge proposed | Model over-merging | `merge_veto` blocks it (numbers, versions, qualifiers) | Done |
| `GraphLoadError`: name not allowed by the ontology | Bad data, injection attempt | Load stops. Only ontology-checked names may enter a query text; everything else is a parameter | Done |
| `GraphLoadError`: entity or edge has no evidence unit, edge points at a missing entity, entity has no vector, schema script changed after it was applied | Inconsistent data | Load stops with the exact reason | Partly: stops, but I did not verify that a stopped load leaves nothing half-written |
| `CommunityError`: edge or parent missing | Inconsistent graph | Clustering stops with the reason | Done |
| Community report is not valid, has no valid citation, or is cut off | Model | Asked again (up to 3), invalid citations are removed; unusable report fails for that community; re-run regenerates only what changed | Done |
| Cost cap reached in reports | Budget | New calls stop; finished reports stay | Done |

## 5. Answering questions (Phases 1, 3, 4)

| Situation | What the person gets | Status |
|---|---|---|
| Empty question, longer than 4,000 characters (`AnswerError`, `EmptyQuestion`) | Clear message, no model call | Done |
| Key, token or email inside a question | Redacted before anything is logged or sent | Done |
| No entity close enough (vector score under 0.79) | **Refusal** with a hint to name a method or dataset | Done (but 2 of 10 unanswerable test questions were answered wrongly: a generic word or a model name matched an entity) |
| Evidence too thin | **Refusal** | Done |
| Two entities of the same type share a name | **Clarify** question | Done |
| Model cannot be reached | **Refusal** "model could not be reached, try again" with the cost counted | Done |
| Answer cites a label that is not in the context | Citation check status `warning`; the chip shows as missing | Done |
| Sentence names an entity not in the context | `warning` | Done |
| Global search: some map batches fail | Answer is marked **partial** and says so; failed batches still count in cost | Done |
| Router model unusable or unavailable | Falls back to local mode and tells the person why | Done |
| Neo4j, Qdrant or Postgres down while a command line search runs | The Python exception stops the command; no retry | **Gap**: acceptable for a command line, not for a service (see section 9) |
| Judge or support check gives no usable verdict (evaluation only) | Retried, then that item is marked failed and reported | Done |

## 6. The API (Phases 5 and 6)

Every error body has the same shape: `{"error": {"code": "...", "message": "..."}}`. The input is
never echoed back.

| HTTP | `code` | Cause | Handling | Status |
|---|---|---|---|---|
| 422 | `invalid_request` | Wrong type, empty or over-long question, unknown field, bad id, bad `limit` | Names the field only | Done |
| 401 | `visitor_required` | Token missing, forged, expired or its visitor was deleted | Web server fetches a new token and retries once | Done |
| 503 | `visitor_not_configured` | `VISITOR_TOKEN_SECRET` empty | No token is issued or trusted | Done |
| 404 | `unknown_answer`, `not_found` | Row does not exist **or belongs to someone else** (same answer for both) | No hint whether the id exists | Done |
| 429 | `rate_limited` | Per visitor, per address or admin-guess limit | `Retry-After` header, plain wait time | Done |
| 429 | `daily_limit` | Daily cost cap reached | Message says to try tomorrow | Done (tested with a fake paid model only) |
| 503 | `limiter_unavailable` | Redis down | Request refused (fail closed) | Done (owner decision in section 9) |
| 503 | `engine_unavailable` | No answer engine configured | Plain message | Done |
| 411, 413 | `length_required`, `too_large` | POST or PUT without length, or over 32 KB | Refused before the body is read | Done |
| 401, 403 | `unauthorized`, `admin_disabled` | Wrong or missing admin key, or no key configured | Audit row written; guessing is limited | Done |
| 500 | `internal_error` | Any unexpected exception | Generic message; log has only the exception type and request id | Done |
| 200 with `saved: false` | | Saving the answer failed | The answer is still shown, rating and saving are switched off | Done |
| 503 | `storage_unavailable` | Postgres down, connection lost, or no free connection | `Retry-After: 5`, plain message, log has only the exception type and request id; connect timeout is 3 seconds. Other database errors (a broken query) stay a generic 500 because they are our bugs | Done (5 tests; live: database stopped, then started again) |
| 503 | health | `GET /api/v1/health` when any of the four services is down | Reports which one | Done |
| Time | | A request that runs too long | No per-request time limit yet | **Gap**: needed when live answers arrive (Phase 7) |

## 7. The web server and the screen

| Situation | What happens | Status |
|---|---|---|
| API not reachable from the web server | 502 `api_unreachable`; the screen shows "The API is not reachable right now" | Done (checked in the browser) |
| Network down in the browser | "Could not reach the server. Is it running?" | Done (checked) |
| 429 | The API's wait message is shown in a red notice | Done (checked) |
| Non-JSON POST or PUT, cross-site request, oversized body, bad id | 415, 403, 413, 422 before anything reaches the API | Done |
| Refusal or clarify | Shown as a plain notice, not as an error | Done |
| Hostile text in an answer (script, image tags) | Shown as text; the CSP also blocks inline handlers, other-site frames and other-origin requests | Done (checked in the browser) |
| `localStorage` blocked | Theme still works for the session | Done |
| Rating or saving fails | Short message next to the button | Done |
| Example list cannot load | The list is simply empty (no message) | Partly (harmless) |
| An exception while a React component renders | `app/error.tsx` shows a plain message, a short reference code and a "Try again" button; `app/global-error.tsx` does the same if the layout itself fails. The error text is never shown | Done for a failing page (checked in the browser with a temporary crashing page); `global-error.tsx` is built but was not triggered |
| Cookie rejected by the browser | Every request makes a new visitor, so history never appears | Partly: limited to 10 new visitors a minute per address; no message |

## 8. Infrastructure and configuration

| Situation | What happens | Status |
|---|---|---|
| Docker engine stopped (seen after a reboot) | Commands fail with an engine message | Manual: start Docker Desktop and re-run |
| Slow or dropped network (PyPI, npm, GitHub, OpenAI) | Retry loops and caches in the image builds; push retried in scripts | Partly |
| Redis down | Asks and data routes are refused with 503 | Done |
| Postgres down | API answers 503 `storage_unavailable` and recovers when Postgres is back | Done |
| Neo4j or Qdrant down | Health reports it; the command-line search fails (see section 5) | Partly |
| Secrets missing (`PROXY_SECRET`, `ADMIN_API_KEY`) | Address falls back to the socket address; status page stays off | Done |
| Disk full, corrupted volume, lost database | Not handled | **Gap**: no backup or restore yet (Phase 7) |
| Nobody notices a failure | Only JSON logs; no alerts or dashboards (D55) | **Gap** by decision |

## 9. What is still open

1. **Per-request time limit and a short retry with back-off** for Neo4j and Qdrant calls when live
   answers are wired in (Phase 7).
2. **Decision for you:** Redis down currently **blocks** answers (fail closed). The alternative is
   to allow answers without limits (fail open), which is friendlier but removes the cost and abuse
   protection. I recommend keeping fail closed.
3. **Backup and restore** of Postgres and the Neo4j volume before any real use (Phase 7).
4. `global-error.tsx` has not been triggered; it only matters if the layout itself fails.
