# Phase 8 brief: v1.5

Status: **plan updated with the owner's answers of 2026-10-29, waiting for final approval. Nothing is built.**

## Goal

Two parts, chosen by the owner: (A) faster and better answers, (B) real sign-in with password reset.
The bigger corpus (old Part C) is **dropped from v1.5** because the owner cannot raise the OpenAI
limit (see D72). Hosting, HTTPS and monitoring stay out ([LIMITS.md](../../LIMITS.md)). The blueprint
text for v1.5 is not in the repository, so this scope comes from the owner's choices.

## Part A: faster and better answers

Missed in Phase 7: correctness 70% (target 75%), gap +13.3 (target +15), p95 10.3 s (target 8 s).

| Step | Idea | Why it might help | Cost to test (estimate) |
|---|---|---|---|
| A1 | Streaming of the answer text | The first words appear in about 1 s instead of 5 s; total time is unchanged | free |
| A2 | Shorter answer limit (about 150 words instead of 250) | The model call is most of the 5 s | about $0.12 to $0.14 (one hard-set run) |
| A3 | Better choice of passages inside the 8,000-token context (a reranker or a better score) | Only about 57% of the right passages fit today (D68) | download (size shown first, needs your yes) plus about $0.15 |
| A4 | Retry on relate path search and plain-RAG retrieval; declare `uvicorn` in the pipeline lock | Closes two known reliability gaps | free |

Rule: every variant gets its own system name and is judged on the same 30 hard questions, compared
question by question with Phase 7. A change is kept only if it helps and does not hurt the easy set or
the refusal set. If nothing reaches the targets, they stay reported as missed. Cap for Part A: **$0.60**.

## Part B: sign-in with password reset (D70)

Accounts on top of the anonymous visitors; anonymous mode keeps working. Free: no email service.

- **Sign-up:** email and password. The password is hashed with **argon2id**; it is never stored in plain
  text and never logged. Minimum length 10, a list of very common passwords is refused.
- **Password reset without email (because magic links and email services cost money):**
  1. **Recovery codes.** At sign-up the user gets 8 single-use recovery codes, shown **once** (the
     server keeps only hashes). Reset = email + one recovery code + new password. A used code is
     burned; the user can make a new set after signing in.
  2. **Owner-issued reset.** On this local installation the owner (holder of the admin key) can issue a
     one-time reset link for an account that lost its codes. The link works once and expires in 30 minutes.
  3. Honest limit: with no email, a user who loses both the password and the codes depends on the owner.
     That is acceptable for a local, single-owner installation and is written in [LIMITS.md](../../LIMITS.md).
- **Safety measures (my responsibility):** login and reset rate limits per address and per account with
  growing delay; the same generic error for unknown email and wrong password (no account enumeration);
  constant-time checks; reset invalidates all sessions of that account; session cookie rules as in
  Phase 6 (HttpOnly, SameSite, rotated on login); delete-account removes all rows; audit log for logins,
  failures, resets and admin-issued links; tests that a user never sees another user's rows.
- **Claiming anonymous data:** opt-in, one time, from the same browser.
- Schema: the `users` table already exists; a migration adds password hash, recovery code hashes and
  reset tokens. A threat list is written **before** the code. No claim of "secure" without an outside review.

## Dropped from v1.5 (to the backlog)

Bigger corpus and incremental updates (`add-papers`); the pypdf upgrade with re-extraction. Reason: they
cost real OpenAI money (about $7 to $8 per 100 papers, plus $2.40 to re-extract the 25 papers for the
pypdf upgrade) and the owner cannot raise the monthly limit. D59 stays in force: the corpus is fixed and
hash-pinned, nobody uploads PDFs. They return only after the owner raises the limit and approves a new estimate.

## Decisions (final, owner's words of 2026-10-29)

| # | Decision | Result |
|---|---|---|
| D69 | Order A then B; tags `phase-8a`, `phase-8b`; `v1.5` after B | Accepted (default recommendation) |
| D70 | Sign-in: email and password with argon2id **and a password reset**; no magic link (costs money); no paid email service; reset by recovery codes and owner-issued link | **Owner chose reset; I chose the free mechanism** |
| D71 | pypdf upgrade | **Not now** (costs $2.40 and the limit cannot be raised); D59 stays |
| D72 | Corpus size | **Stays at 25 papers**; the growth part is dropped from v1.5 |
| D73 | Spend cap | Part A $0.60, Part B $0; every paid batch needs a shown estimate and your yes |

## Build steps (after your final approval)

1. A1 to A4, measure, report; stop for the owner's keep-or-drop gate.
2. Part B: threat list, migration, API, web screens (sign up, sign in, reset, recovery codes, delete
   account), tests, two-account check in the browser, updated audit.
3. Release: README table regenerated if numbers changed, docs, tags, A to J report, approval, PR and CI.

## Risks

- Part A may not reach the targets; then they stay reported as missed.
- Sign-in adds real attack surface (password guessing, enumeration, session theft, recovery-code theft).
  Mitigations are listed above; no outside review.
- The monthly OpenAI spend is already high; Part A is small (about $0.30 in total) but I stop if the
  limit is reached.
