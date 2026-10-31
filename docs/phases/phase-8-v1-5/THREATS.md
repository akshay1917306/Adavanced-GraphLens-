# Part B threat list: sign-in with password reset

Written **before any code** (Phase 8, Part B). It lists what can go wrong, what the design does about
it, and what stays open. It is a list made by the builder, not an outside review. Nothing here lets
anyone call the system "secure".

## What we protect

| Asset | Why it matters |
|---|---|
| Passwords | People reuse them; a leak harms them elsewhere |
| Recovery codes and reset links | Each one is a password for one reset |
| Session cookies | Whoever holds one is that user |
| Conversations, saved answers, feedback, preferences | The only personal data we keep |
| The admin key | Issues reset links; reads the status page |
| The signing secrets (`VISITOR_TOKEN_SECRET`, `PROXY_SECRET`) | Forge tokens, fake client addresses |

## Who attacks

1. A stranger on the internet or the same network, with no account (guessing, flooding, scraping).
2. A signed-in user who tries to see or change another user's data.
3. Someone who stole a laptop, a cookie, a backup file, or a log.
4. A user who forgot their password and codes (not an attacker, but the reset path is the weak point).

## Threats, measures, what stays open

| # | Threat | Measure in the design | Test (planned) | Still open |
|---|---|---|---|---|
| T1 | Password guessing and credential stuffing on sign-in | Rate limit per address (IP) **and** per account, the account limit counts by a hash of the typed email, so it is the same for known and unknown emails (10 tries per 15 minutes); there is no sleep-delay and no lock flag in the database, because either would show which emails exist; password at least 10 characters; a bundled list of common passwords refused; argon2id so each guess is expensive | 11th wrong try is refused with `429` and `Retry-After`; locked account still answers the same generic text | A patient attacker with many addresses can still try a few guesses a day per account; no second factor |
| T2 | Account enumeration (is this email registered?) | Same text and same status for unknown email and wrong password; **sign-up does say "This email cannot be used" when the email exists** (without email, no way around that: a fake success would hand out codes for an account that is not yours); sign-up is limited to 5 per hour per address to slow collecting; the work of one argon2 check is done even for an unknown email, so the time is alike; reset also answers the same | Responses and timing buckets of known vs unknown email compared | Timing differences below what the test can see; sign-up reveals that an email exists; the owner-issued link route answers 404 for an unknown email, to the admin only |
| T3 | Recovery code theft or guessing | 8 codes of 12 characters (60 bits) from a restricted alphabet; shown once; only argon2id hashes stored; each code single-use; failed code tries count toward the same per-account and per-address limits; using a code writes an audit row; a **new** set replaces all old codes | A used code fails the second time; 20 wrong codes lock the reset | A user who photographs or emails the codes to themselves moves the risk to that place; we cannot prevent it |
| T4 | Session theft (cookie stolen, or XSS reads it) | Session cookie is `HttpOnly`, `SameSite=Lax`, `Secure` when `COOKIE_SECURE=1`; the browser JavaScript never sees the token (the web server holds it, as in Phase 6); CSP with nonce stays; server-side session rows can be revoked; sessions expire (30 days idle, 90 days absolute) | Cookie flags checked; revoked session refused | Over plain `http` (the local default) a network observer can read the cookie and the password. **HTTPS is not part of v1.5.** Do not host this publicly without it |
| T5 | Cross-site request forgery (a bad page makes the browser post sign-out, delete, reset) | `SameSite=Lax` cookie; state-changing routes are `POST`/`DELETE` with `Content-Type: application/json` only, and the web proxy refuses a request whose `Origin` is not its own; delete-account also needs the password again | Cross-origin post refused | Browsers that ignore SameSite (old ones) |
| T6 | Session fixation | A new session id and cookie are issued at every sign-in and after every reset; the anonymous token is never promoted | Id before and after sign-in differ | none known |
| T7 | Reset abuse (take over an account by resetting) | Reset needs **a valid recovery code** or an owner-issued link; neither can be requested by the account holder through the public API without them; a reset burns the code used, ends all sessions of the account and writes an audit row; the reset answer is generic (the user is told to make a new set of codes after signing in) | Reset with a wrong code, an old link, or an expired link fails with the same text | If the attacker has a user's recovery codes they own the account (by design; that is what the codes are) |
| T8 | Owner-issued link leaked (log, chat, browser history, referrer) | The link holds a random 256-bit token; only its hash is stored; it works once, expires in 30 minutes, is accepted only by a `POST` (the token is never a query parameter on the API; the web page reads it from the URL fragment, which browsers do not send to servers or in a `Referer`); the page removes the fragment from the address bar after reading it; the link is shown once to the owner and never logged | Link twice → second fails; link after 31 min fails; token string not found in any log line | The owner pastes the link somewhere unsafe; a link is a password for 30 minutes |
| T9 | Admin key stolen or guessed | Admin routes already rate limited and compared in constant time (Phase 6); issuing a link is audited with the target account id; the key is in `.env`, never in the browser | Wrong key → `401`, rate limit holds | The key is one shared secret; anyone with it can reset any account. Acceptable for one owner on one machine |
| T10 | Database or backup leaks | Passwords and codes only as argon2id hashes (parameters: memory 19 MiB, 2 passes, 1 lane, per-hash random salt); reset tokens and session secrets only as SHA-256 of 256-bit random values (high entropy, so a fast hash is safe); `backups/` stays git-ignored; backups are not encrypted (see RUNBOOK) | Hash format and no plain secret in a dump (grep test on a test database) | Backup files are readable by anyone with the disk; emails are stored in clear |
| T11 | One user reads or changes another user's rows (IDOR) | Every data route keeps resolving the owner from the session on the server, never from a body or URL id; an account has exactly one home visitor id, so existing ownership checks (`WHERE visitor_id = …`) keep working unchanged | A test for **every** route that account B gets `404` for account A's ids; two-account check by hand | A bug in a route added later; the tests must be extended with each new route |
| T12 | Passwords, tokens or emails written to logs or error pages | Request bodies of the auth routes are never logged; error handlers print only the exception type; the audit log stores the account id, not the email or any secret; `repr` of models with secrets is masked | grep of container logs after a test run for the test password, code and token | Reverse proxies or tools added later may log bodies |
| T13 | Denial of service through the expensive hash | Argon2 runs in a bounded worker pool (at most 2 at once, others wait up to 2 s then get `503`); sign-in and sign-up have their own per-address limits that are stricter than the normal ones; request size capped at 2,000 characters | Burst of sign-ins does not stop `/ask` or `/health` | A distributed flood can still make sign-in unavailable (anonymous use keeps working) |
| T14 | Sign-up spam (fill the table) | Per-address limit (5 per hour), a cap on total users that the owner sets (default 200), email format and length checks | The 6th sign-up in an hour is refused | A determined attacker with many addresses can reach the cap and block honest sign-ups |
| T15 | Email is not proven (no email service) | The email is only a username. We **do not** claim it belongs to the person, we send nothing to it, and the screen says so | n/a | Someone can register another person's email; they get an empty account, not that person's data |
| T16 | Claiming anonymous data steals someone else's history | Claim is one time, only moves the data of the **anonymous visitor in the same browser** (valid anonymous token needed) into the account being signed in, needs the password again, and cannot be undone; an anonymous visitor that was already claimed cannot be claimed again | Claim twice fails; claim with another visitor's token fails | Someone using a shared browser can claim the earlier person's anonymous history |
| T17 | Delete account goes wrong or is abused | Needs the password, deletes the user, the home visitor and its rows in one transaction, ends all sessions, audits the deletion without the email; copies in older backups remain until those are deleted | Rows gone in every table; a second delete fails | Backups |
| T18 | A forgotten password and lost codes | The owner can issue a link (T8). Without the owner there is no way back, by design | n/a | Documented in LIMITS.md |
| T19 | A weak dependency (argon2 library) | Use the maintained `argon2-cffi` pinned to an exact version at least two weeks old, added to `uv.lock`, covered by the existing `pip-audit` job | `pip-audit` green | A new library is new attack surface |
| T20 | Replay and anonymous mode stay open | Anonymous visitors keep working with their limits; signed-in users get the same limits (no free pass); nothing in Part B changes the answer path | Existing 167 API tests still pass | Sign-in does not make answering safer, only attributes data |

## Out of scope for Part B (said plainly)

- No two-factor sign-in, no email verification, no "sign in with Google".
- No HTTPS, no outside penetration test, no bug bounty. Until an outside review, the right words are
  "built with the measures above", never "secure".
- No password strength meter based on a big breach list (we ship a small list; length matters more).

## Review of this list

Before code: the owner reads this file and the design in `DESIGN-B.md`, and answers the open questions
at the end of that file. Code starts only after that.
