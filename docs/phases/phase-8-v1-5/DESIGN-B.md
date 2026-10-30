# Part B design: sign-in with password reset

Companion of [THREATS.md](THREATS.md). Nothing here is built yet.

## Idea in one paragraph

Today every person is an anonymous **visitor** with a signed token, and all data (conversations,
saved answers, feedback, preferences) hangs on `visitors.id`. An account is a `users` row that owns
exactly **one home visitor**. Signing in gives the browser a **session** that resolves to that home
visitor, so every existing route and every existing ownership check keeps working unchanged. Anonymous
visitors keep working exactly as before.

We used a "home visitor" because it keeps the number of changed routes at zero and lets the existing
tests keep proving that nobody reads another visitor's rows. We did not choose a second `user_id` column
on every table because each new column is one more place for an ownership check to be forgotten.

## Data (one migration, `0002_accounts.py`)

| Table / column | Content |
|---|---|
| `users` (exists) + `password_hash text`, `home_visitor_id uuid unique`, `failed_logins int`, `locked_until timestamptz`, `last_login_at` | argon2id hash; the one visitor that holds the account's data |
| `sessions` | `id uuid`, `user_id`, `secret_hash` (SHA-256 of a 256-bit secret), `created_at`, `last_used_at`, `expires_at`, `revoked_at` |
| `recovery_codes` | `id`, `user_id`, `code_hash` (argon2id), `used_at`, `batch int` |
| `reset_tokens` | `id`, `user_id`, `token_hash` (SHA-256), `expires_at` (30 min), `used_at`, `issued_by` (admin audit id) |
| `admin_audit_log` (exists) | rows for sign-up, sign-in, failure (account id only), reset by code, reset by link, link issued, new codes, delete |

Rules: emails are lower-cased and trimmed, unique; `deleted_at` stays but delete-account really removes
the rows (T17). The migration is reversible and tested on a throwaway database.

## Tokens

- Anonymous token: unchanged, `v1.<visitor>.<expiry>.<hmac>`.
- Session token: `s1.<session id>.<secret>`, sent in the same `X-Visitor-Token` header by the web server.
  The API looks up the session, compares the hash in constant time, checks expiry and revocation, and
  returns the user's **home visitor id**. Everything after that line of code is identical to today.
- The browser keeps only an HttpOnly cookie; the web server adds the header (as it does now).

## API (all under `/api/v1/auth`, JSON only, bodies never logged)

| Route | Needs | Does |
|---|---|---|
| `POST /signup` | email, password, address limit | creates the user, home visitor, session, **8 recovery codes (returned once)** |
| `POST /login` | email, password | generic error on any failure; new session; resets failure counter |
| `POST /logout` | session | revokes this session |
| `POST /logout-all` | session + password | revokes all sessions of the account |
| `GET /me` | session | email, created date, number of unused codes (never the codes) |
| `POST /recovery-codes` | session + password | new set of 8; old unused codes burned; shown once |
| `POST /reset` | email + recovery code + new password | burns the code, sets the password, **revokes all sessions**, new session, audit |
| `POST /reset-with-link` | token + new password | same as above for an owner link |
| `POST /claim` | session + password + anonymous token | moves the anonymous visitor's data into the home visitor, once |
| `DELETE /account` | session + password | deletes everything of the account, ends sessions |
| `POST /api/v1/admin/reset-link` | admin key + email | returns a one-time URL (30 min) once; audited. Same generic reply if the email is unknown |

Web screens: sign up (then "save your recovery codes" page with copy and download, and a tick box "I
saved them" before continuing), sign in, "forgot password" (email + code + new password), "reset with
link" (reads the token from the URL fragment), account page (new codes, sign out everywhere, claim
anonymous history, delete account). Every screen says that the email is **not verified** and that
without codes and owner help a lost password cannot be recovered.

## Limits and numbers (all settings, defaults shown)

| Setting | Default |
|---|---|
| Password length | 10 to 128; refused if on the bundled list of about 500 common passwords, or equal to the email |
| Argon2id | memory 19 MiB, 2 passes, 1 lane (OWASP minimum for argon2id); at most 2 hashes at once |
| Sign-in | 10 per 15 min per address; 10 failures in a row lock the account for 15 min (delay grows 1, 2, 4, 8 s) |
| Reset (code or link) | 10 tries per hour per address and per account |
| Sign-up | 5 per hour per address; total users capped at 200 |
| Session | idle 30 days, absolute 90 days |
| Owner link | 30 minutes, once |

## Order of work after approval

1. Migration + store functions + tests (hashing, codes, tokens, lock, sessions) on a throwaway database.
2. Routes + rate limits + audit + tests including **every data route with two accounts**.
3. Web proxy (second cookie, origin check) + screens + `tsc`, `eslint`, build.
4. Two-account check by hand in the browser, then the grep for secrets in logs.
5. Docs: README, LIMITS, RUNBOOK (admin link command), STATUS, WALKTHROUGH, A to J report; owner approval; PR; CI; tag `phase-8b`, then `v1.5`.

Cost: **$0** (no model call). Downloads: one Python library, `argon2-cffi` (a few hundred KB), pinned,
to be approved by the owner with its name and size before it is added.

## Questions for the owner (answer before code starts)

1. **Is "email not verified" acceptable?** (No email service means we cannot prove an address is yours.)
2. **Total user cap 200** and **sign-up 5 per hour per address**: keep, or change?
3. **Sessions 30 days idle / 90 days total**: keep, or shorter?
4. **Download `argon2-cffi`** (about 0.1 MB wheel plus a tiny C part, MIT license): yes or no?
5. Do you want the owner reset link to be created by a **terminal command** (`scripts/reset-link.sh email`) as well as the API route? (Recommended: yes, because the admin key then never has to be typed into a browser.)
