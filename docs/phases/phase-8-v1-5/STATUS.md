# Phase 8 status

Last updated: 2026-10-29

## State

**Plan approved by the owner on 2026-10-29. Part A step A1 (streaming) is built and tested with fakes; measured live (see below).** Branch `phase-8/v1-5` from
`main` at eca204a. Nothing built, nothing spent, nothing pushed. Scope: faster and better answers (A) and sign-in with password reset (B). The bigger corpus is dropped
(the owner cannot raise the OpenAI limit); hosting is out.

## A1 streaming (built)

- Model client: `OpenAiLlm.complete(..., on_delta=...)` streams the text and returns the same result
  (tokens, cost, finish reason) as before; a JSON-schema call is never streamed. A small hook
  (`set_delta_sink`, `delta_kwargs`) lets the search service stream only the main answer of local,
  relate and plain-RAG modes; the comparison answer and global search are not streamed.
- Search service: `POST /search/stream` (lines of JSON: `delta`, then `final` or `error`), same key, slots
  and 40 s deadline as `/search`.
- API: `POST /api/v1/ask/stream` with the same limits, cost counting and saving as `/ask`; problems before
  the first byte are normal HTTP errors; a failure in the middle is one `error` line and nothing is
  charged or saved; replay mode answers with one `final` line.
- Web: `/api/ask/stream` passes the stream on; the screen shows a dashed "Draft" card while the text
  arrives (shown as plain text), then replaces it with the checked answer, which may differ or refuse.
- Tests: pipeline 481 pass (10 new), API 167 pass (17 new), ruff, eslint, tsc and the Next build pass.
- **Measured live (2026-10-29, owner's yes, 3 local questions, cost $0.0091 in total):** first draft
  word after 7.3 s, 4.4 s, 4.8 s; checked final answer after 9.4 s, 7.0 s, 7.8 s; all `answered` and
  `verified`; answers of 143, 245 and 222 words. The draft starts about 2 to 3 s before the end, because
  routing and retrieval run before the model writes. The gain is real but modest; the answer length (A2)
  and retrieval time matter more. Not seen: the draft card with a real stream in the browser.

## Incident while testing (my mistake, repaired)

I ran the API test suite once against the **live** database. Its `test_store` fixture deletes all
conversations, visitors and audit rows, so those tables were emptied. I restored them from today's
backup (`backups/20261029-143225`): 7 visitors, 9 conversations, 18 messages, 9 answer rows are back.
Rows made after that backup (a few check-script questions) are gone. The suite has since run only
against a throwaway database `graphlens_test`, which was dropped afterwards.

## Decisions waiting for the owner

Final approval of D69 to D73 as updated in `BRIEF.md` (sign-in with reset by recovery codes and owner-issued link; corpus stays 25; no pypdf upgrade; Part A cap $0.60).

## Open from Phase 7

Owner review of the Phase 3 and Phase 4 pages and the 10 + 10 spot-check (see Phase 7 CHECKLIST).

## Blockers

None.

## Exact next action

Owner: yes or no to a live check of streaming (about $0.01). Then A2 (shorter answer limit, about $0.13).

## A2 shorter answers (tried, 2026-10-29, owner's yes, cap $0.20)

Same 30 hard questions as Phase 7; prompt "at most 150 words" (was 250), output limit 500 tokens (was 800).
Result file: `data/eval/phase8/a2-short150.json`. Cost $0.0937 of the $0.60 Part A cap (total Part A so far about $0.10).

| | Phase 4/7 (250 words) | A2 (150 words) |
|---|---|---|
| Correct | 21 of 30 (70%) | 22 of 30 (73.3%, 56 to 86%) |
| Citation check | 27 verified, 3 warnings | 25 verified, 5 warnings |
| Answer cost per question | about $0.0031 to $0.0035 | $0.0029 |
| Mean time | 5.2 to 5.8 s | **6.35 s** |

Against the earlier answers question by question: 3 better, 26 same, 1 worse. **The agreed keep rule
(time about 0.7 s faster) is NOT met: the mean time was not lower** (the earlier numbers were taken on
another day and the network time varies, so this is a noisy comparison, not a proof that it is slower).
Correctness did not drop, cost per answer fell about 10 to 17%, and 2 more citation warnings appeared.
The code change was reverted (working tree back to 250 words) until the owner decides.

## A3 passage choice, free offline test (2026-10-29, no model, $0, no download)

Question: of the gold passages of the 30 hard questions, how many are really shown inside the 8,000-token
context? (script: `a3_offline_test.py`, run in the pipeline image; same questions as Phase 7.)

| Variant | Gold passages shown | Questions with all gold shown | Passages shown |
|---|---|---|---|
| 0 today (plain top 6, passages 45%, cap 450 tokens) | 57% | 9 of 30 | 11.1 |
| 1 plain top 10 | 67% | 12 | 11.3 |
| 2 plain top 8 | 58% | 10 | 11.2 |
| 3 passage share 60% (community reports 5%) | 67% | 13 | 14.4 |
| 4 passage cap 300 tokens | 63% | 11 | 14.0 |
| **5 plain top 10 + cap 300 + passage share 60%** | **72%** | **15** | 18.4 |
| 6 citation weight 0.0 / 0.3 / 0.7 | 57% / 57% / 55% | 8 / 9 / 8 | about 11 |

Variant 0 reproduces the 57% of D68, so the test measures the same thing. Variant 5 shows 15 points more
gold passages with the same 8,000 tokens (so about the same cost per answer). What this does **not**
tell: whether the answers get better. Risks to check in the paid run: fewer community reports (5% instead
of 20%) and passages cut to 300 tokens may hide the sentence that is needed.

## A3 passage choice, paid hard-set check (2026-10-29/30, owner's yes, cap $0.20)

Variant 5 built into the code: plain top 10 first, passages cut at 300 tokens, passage share 60%,
community reports 5% (`localcontext.py`, `_local_deps`). Result file: `data/eval/phase8/a3-ctx-v5.json`.

| | Phase 4/7 (today) | A3 variant 5 |
|---|---|---|
| Correct (30 hard questions) | 21 (70%) | **23 (76.7%, interval 59 to 88%)** |
| Question by question | | 4 better, 23 same, 3 worse |
| Citation check | 27 verified, 3 warnings | 26 verified, 4 warnings |
| Mean time | 5.2 to 5.8 s | 5.77 s |
| Answer cost per question | about $0.0031 to $0.0035 | $0.0035 |

The keep rule (correct at least 70%, at most 5 warnings, time not worse) is met. 76.7% is above the 75%
target of Phase 7, but one question is 3.3 points and the intervals overlap with 70%, so this is
**not proof** of a better system, and the hard set is the same 30 questions used to tune it (the owner's
review of those labels is still open). Spend: the first run's output was hidden by my own output filter
(exit code 4, a mistake of mine), so I ran the same command again; most answers came from the cache.
The paid answers cost $0.106 in total; with judging the A3 run is about $0.14 (estimated, not exact).
Part A spend so far, estimated: A1 $0.009 + A2 $0.094 + A3 about $0.14 = about $0.24 of $0.60.
Pipeline tests 481 pass (two budget tests updated to the new 60% share), ruff clean.
