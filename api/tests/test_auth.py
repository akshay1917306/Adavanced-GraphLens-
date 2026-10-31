"""Sign-in on a disposable Postgres (set DATABASE_URL; skipped otherwise).

Never run this against the live database. Every test uses its own random emails and removes only
its own accounts afterwards.
"""

import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, text

from app import auth as auth_module
from app import main
from app import visitor as visitor_module
from app.accounts import Accounts
from app.config import get_settings
from app.passwords import (
    check_password,
    new_recovery_codes,
    normalise_code,
    verify_secret,
)
from app.ratelimit import RateLimited, get_limiter
from app.store import Store

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery 42"
OTHER = "another long passphrase 77"
# made up for each run, so no key-like text sits in the repository
ADMIN_KEY = uuid.uuid4().hex
VISITOR_SECRET = uuid.uuid4().hex
WRONG = "not-" + uuid.uuid4().hex[:10]


def settings_with(**fields):
    return get_settings().model_copy(update=fields)


@pytest.fixture
def env(migrated_db, monkeypatch):
    engine = create_engine(migrated_db)
    accounts, store = Accounts(engine), Store(engine)
    patched = settings_with(
        admin_api_key=SecretStr(ADMIN_KEY),
        visitor_token_secret=SecretStr(VISITOR_SECRET),
        max_users=1000,
    )
    monkeypatch.setattr(auth_module, "get_settings", lambda: patched)
    monkeypatch.setattr(visitor_module, "get_settings", lambda: patched)
    from app import accounts as accounts_module

    main.app.dependency_overrides[accounts_module.get_accounts] = lambda: accounts
    main.app.dependency_overrides[main.get_store] = lambda: store
    client = TestClient(main.app, raise_server_exceptions=False)
    created: list[str] = []
    anonymous: list[uuid.UUID] = []
    yield type("Env", (), {"client": client, "engine": engine, "created": created,
                           "accounts": accounts, "store": store, "settings": patched,
                           "anonymous": anonymous})  # fmt: skip
    with engine.begin() as conn:
        for visitor in anonymous:
            conn.execute(text("DELETE FROM visitors WHERE id = :v"), {"v": visitor})
        for email in created:
            conn.execute(
                text(
                    "UPDATE admin_audit_log SET user_id = NULL "
                    "WHERE user_id IN (SELECT id FROM users WHERE email = :e)"
                ),
                {"e": email},
            )
            conn.execute(
                text("DELETE FROM visitors WHERE user_id IN (SELECT id FROM users WHERE email=:e)"),
                {"e": email},
            )
            conn.execute(text("DELETE FROM users WHERE email = :e"), {"e": email})
    main.app.dependency_overrides.pop(accounts_module.get_accounts, None)
    main.app.dependency_overrides.pop(main.get_store, None)
    engine.dispose()


def anonymous_visitor(env):
    visitor = env.store.create_visitor()
    env.anonymous.append(visitor)
    return visitor


def email_for(env):
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    env.created.append(email)
    return email


def signup(env, email=None, password=PASSWORD):
    email = email or email_for(env)
    response = env.client.post("/api/v1/auth/signup", json={"email": email, "password": password})
    return email, response


def headers(token):
    return {"X-Visitor-Token": token}


def new_user(env):
    email, response = signup(env)
    assert response.status_code == 200, response.text
    data = response.json()
    return email, data["token"], data["recovery_codes"]


def first_question(env):
    return env.client.get("/api/v1/examples").json()["questions"][0]


# ---------------------------------------------------------------- pure rules


def test_password_rules():
    assert check_password("short", "a@b.co")
    assert check_password("password123", "a@b.co")
    assert check_password("aaaaaaaaaaaa", "a@b.co")
    assert check_password("anna.smith", "anna.smith@example.com")
    assert check_password(PASSWORD, "a@b.co") is None


def test_recovery_codes_have_the_right_shape_and_can_be_typed_loosely():
    codes = new_recovery_codes()
    assert len(set(codes)) == 8 and all(len(c) == 14 and c.count("-") == 2 for c in codes)
    assert normalise_code(codes[0].lower().replace("-", " ")) == normalise_code(codes[0])


def test_an_unknown_account_still_costs_one_hash():
    assert verify_secret(None, "whatever") is False


# ---------------------------------------------------------------- sign up and in


def test_sign_up_gives_a_session_and_eight_codes_once(env):
    email, token, codes = new_user(env)
    assert len(codes) == 8 and token.startswith("s1.")
    me = env.client.get("/api/v1/auth/me", headers=headers(token)).json()
    assert me == {"email": email, "unused_recovery_codes": 8}
    assert "recovery_codes" not in me


def test_sign_up_refuses_weak_passwords_and_taken_emails(env):
    _, weak = signup(env, password="password123")
    assert weak.status_code == 422 and weak.json()["error"]["code"] == "weak_password"
    email, _, _ = new_user(env)
    again = env.client.post("/api/v1/auth/signup", json={"email": email, "password": OTHER})
    assert again.status_code == 409


def test_sign_up_stops_at_the_owner_cap(env, monkeypatch):
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings_with(max_users=0))
    _, response = signup(env)
    assert response.status_code == 403 and response.json()["error"]["code"] == "signups_closed"


def test_wrong_password_and_unknown_email_look_the_same(env):
    email, _, _ = new_user(env)
    wrong = env.client.post("/api/v1/auth/login", json={"email": email, "password": "nope" * 4})
    unknown = env.client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "nope" * 4}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_login_works_and_gives_a_new_session_each_time(env):
    email, first, _ = new_user(env)
    second = env.client.post(
        "/api/v1/auth/login", json={"email": email.upper(), "password": PASSWORD}
    )
    assert second.status_code == 200 and second.json()["token"] != first
    assert (
        env.client.get("/api/v1/auth/me", headers=headers(second.json()["token"])).status_code
        == 200
    )


def test_nothing_secret_is_stored_in_plain_text(env):
    email, token, codes = new_user(env)
    secret = token.split(".")[2]
    with env.engine.begin() as conn:
        user = conn.execute(
            text("SELECT id, password_hash FROM users WHERE email = :e"), {"e": email}
        ).one()
        hashes = [r[0] for r in conn.execute(
            text("SELECT code_hash FROM recovery_codes WHERE user_id = :u"), {"u": user[0]}
        )]  # fmt: skip
        session_hash = conn.execute(
            text("SELECT secret_hash FROM sessions WHERE user_id = :u"), {"u": user[0]}
        ).scalar_one()
    assert user[1].startswith("$argon2id$") and PASSWORD not in user[1]
    assert len(hashes) == 8 and all(h.startswith("$argon2id$") for h in hashes)
    assert not any(normalise_code(c) in h for c in codes for h in hashes)
    assert secret not in session_hash and len(session_hash) == 64


def test_logging_never_contains_the_password_code_or_token(env, caplog):
    caplog.set_level(logging.DEBUG)
    email, token, codes = new_user(env)
    env.client.post("/api/v1/auth/login", json={"email": email, "password": WRONG})
    env.client.post(
        "/api/v1/auth/reset",
        json={"email": email, "recovery_code": codes[0], "new_password": OTHER},
    )
    text_ = caplog.text
    for secret in (PASSWORD, OTHER, codes[0], normalise_code(codes[0]), token.split(".")[2]):
        assert secret not in text_


# ---------------------------------------------------------------- sessions


def test_logout_ends_only_that_session_and_logout_all_ends_every_one(env):
    email, first, _ = new_user(env)
    second = env.client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["token"]
    assert env.client.post("/api/v1/auth/logout", headers=headers(first)).status_code == 200
    assert env.client.get("/api/v1/auth/me", headers=headers(first)).status_code == 401
    assert env.client.get("/api/v1/auth/me", headers=headers(second)).status_code == 200
    wrong = env.client.post(
        "/api/v1/auth/logout-all", headers=headers(second), json={"password": "x" * 12}
    )
    assert wrong.status_code == 401
    env.client.post("/api/v1/auth/logout-all", headers=headers(second), json={"password": PASSWORD})
    assert env.client.get("/api/v1/auth/me", headers=headers(second)).status_code == 401


def test_a_forged_or_expired_session_is_refused(env):
    _, token, _ = new_user(env)
    kind, session_id, secret = token.split(".")
    assert (
        env.client.get(
            "/api/v1/auth/me", headers=headers(f"{kind}.{session_id}.{secret}x")
        ).status_code
        == 401
    )
    assert (
        env.client.get(
            "/api/v1/auth/me", headers=headers(f"{kind}.{uuid.uuid4()}.{secret}")
        ).status_code
        == 401
    )
    with env.engine.begin() as conn:
        conn.execute(
            text("UPDATE sessions SET last_used_at = now() - interval '31 days' WHERE id = :s"),
            {"s": session_id},
        )
    assert env.client.get("/api/v1/auth/me", headers=headers(token)).status_code == 401


# ---------------------------------------------------------------- reset with a recovery code


def test_a_recovery_code_resets_the_password_once_and_ends_old_sessions(env):
    email, old_session, codes = new_user(env)
    body = {"email": email, "recovery_code": codes[0], "new_password": OTHER}
    first = env.client.post("/api/v1/auth/reset", json=body)
    assert first.status_code == 200
    assert env.client.get("/api/v1/auth/me", headers=headers(old_session)).status_code == 401
    assert (
        env.client.get("/api/v1/auth/me", headers=headers(first.json()["token"])).status_code == 200
    )
    again = env.client.post("/api/v1/auth/reset", json=body)  # the same code, now burned
    assert again.status_code == 400
    old = env.client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    new = env.client.post("/api/v1/auth/login", json={"email": email, "password": OTHER})
    assert old.status_code == 401 and new.status_code == 200
    me = env.client.get("/api/v1/auth/me", headers=headers(new.json()["token"])).json()
    assert me["unused_recovery_codes"] == 7


def test_reset_failures_look_the_same_for_unknown_emails_and_wrong_codes(env):
    email, _, codes = new_user(env)
    wrong = env.client.post(
        "/api/v1/auth/reset",
        json={"email": email, "recovery_code": "AAAA-BBBB-CCCC", "new_password": OTHER},
    )
    unknown = env.client.post(
        "/api/v1/auth/reset",
        json={"email": "ghost@example.com", "recovery_code": codes[0], "new_password": OTHER},
    )
    assert wrong.status_code == unknown.status_code == 400 and wrong.json() == unknown.json()
    still = env.client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert still.status_code == 200  # a failed reset changes nothing


def test_a_new_set_of_codes_burns_the_old_ones(env):
    email, token, codes = new_user(env)
    fresh = env.client.post(
        "/api/v1/auth/recovery-codes", headers=headers(token), json={"password": PASSWORD}
    )
    assert fresh.status_code == 200 and len(fresh.json()["recovery_codes"]) == 8
    old = env.client.post(
        "/api/v1/auth/reset",
        json={"email": email, "recovery_code": codes[1], "new_password": OTHER},
    )
    assert old.status_code == 400
    new = env.client.post(
        "/api/v1/auth/reset",
        json={
            "email": email,
            "recovery_code": fresh.json()["recovery_codes"][0],
            "new_password": OTHER,
        },
    )
    assert new.status_code == 200


# ---------------------------------------------------------------- owner link


def link_for(env, email, key=ADMIN_KEY):
    return env.client.post(
        "/api/v1/admin/reset-link", json={"email": email}, headers={"X-Admin-Key": key}
    )


def test_the_owner_link_needs_the_admin_key(env):
    email, _, _ = new_user(env)
    assert link_for(env, email, key="wrong").status_code == 401
    assert env.client.post("/api/v1/admin/reset-link", json={"email": email}).status_code == 401


def test_the_owner_link_works_once_and_ends_sessions(env):
    email, session, _ = new_user(env)
    made = link_for(env, email)
    assert made.status_code == 200 and made.json()["expires_in_minutes"] == 30
    token = made.json()["path"].split("#token=")[1]
    assert "#token=" in made.json()["url"] and "token=" not in made.json()["url"].split("#")[0]
    done = env.client.post(
        "/api/v1/auth/reset-with-link", json={"token": token, "new_password": OTHER}
    )
    assert done.status_code == 200
    assert env.client.get("/api/v1/auth/me", headers=headers(session)).status_code == 401
    again = env.client.post(
        "/api/v1/auth/reset-with-link", json={"token": token, "new_password": OTHER}
    )
    assert again.status_code == 400


def test_the_owner_link_expires_and_a_newer_link_replaces_the_older_one(env):
    email, _, _ = new_user(env)
    first = link_for(env, email).json()["path"].split("#token=")[1]
    second = link_for(env, email).json()["path"].split("#token=")[1]
    older = env.client.post(
        "/api/v1/auth/reset-with-link", json={"token": first, "new_password": OTHER}
    )
    assert older.status_code == 400
    with env.engine.begin() as conn:
        conn.execute(text("UPDATE reset_tokens SET expires_at = now() - interval '1 minute'"
                          " WHERE used_at IS NULL"))  # fmt: skip
    late = env.client.post(
        "/api/v1/auth/reset-with-link", json={"token": second, "new_password": OTHER}
    )
    assert late.status_code == 400


def test_the_token_is_stored_only_as_a_hash(env):
    email, _, _ = new_user(env)
    token = link_for(env, email).json()["path"].split("#token=")[1]
    with env.engine.begin() as conn:
        stored = conn.execute(text("SELECT token_hash FROM reset_tokens")).scalars().all()
    assert token not in stored and all(len(h) == 64 for h in stored)


# ---------------------------------------------------------------- limits


class Counting:
    """Raises RateLimited once a scope was hit more than `limit` times."""

    def __init__(self, limit):
        self.limit, self.seen = limit, {}

    def hit(self, scope, key, limit, window_seconds):
        self.seen[(scope, key)] = self.seen.get((scope, key), 0) + 1
        if self.seen[(scope, key)] > min(limit, self.limit):
            raise RateLimited(60)

    def ensure_room(self, cap_usd):
        return None

    def record_cost(self, usd):
        return None


def make_override(limiter):
    return lambda: limiter


def test_too_many_sign_in_tries_are_refused_for_known_and_unknown_emails_alike(env):
    email, _, _ = new_user(env)
    for address in (email, "ghost@example.com"):
        limiter = Counting(3)
        main.app.dependency_overrides[get_limiter] = make_override(limiter)
        codes = [
            env.client.post(
                "/api/v1/auth/login", json={"email": address, "password": WRONG}
            ).status_code
            for _ in range(5)
        ]
        assert codes[:3] == [401, 401, 401] and codes[3:] == [429, 429]


def test_too_many_reset_tries_are_refused(env):
    limiter = Counting(2)
    main.app.dependency_overrides[get_limiter] = lambda: limiter
    body = {"email": "ghost@example.com", "recovery_code": "AAAA-BBBB-CCCC", "new_password": OTHER}
    codes = [env.client.post("/api/v1/auth/reset", json=body).status_code for _ in range(4)]
    assert codes == [400, 400, 429, 429]


def test_a_flood_of_sign_ups_from_one_address_is_refused(env):
    limiter = Counting(2)
    main.app.dependency_overrides[get_limiter] = lambda: limiter
    codes = [signup(env)[1].status_code for _ in range(4)]
    assert codes == [200, 200, 429, 429]


# ---------------------------------------------------------------- two accounts


def ask_as(env, token, question=None):
    response = env.client.post(
        "/api/v1/ask", json={"question": question or first_question(env)}, headers=headers(token)
    )
    assert response.status_code == 200, response.text
    return response.json()["answer_id"]


def test_one_account_never_sees_or_changes_another_accounts_rows(env):
    _, token_a, _ = new_user(env)
    _, token_b, _ = new_user(env)
    answer_a = ask_as(env, token_a)
    history_a = env.client.get("/api/v1/history", headers=headers(token_a)).json()["items"]
    assert len(history_a) == 1
    conversation_a = history_a[0]["conversation_id"]

    assert env.client.get("/api/v1/history", headers=headers(token_b)).json()["items"] == []
    assert (
        env.client.get(f"/api/v1/history/{conversation_a}", headers=headers(token_b)).status_code
        == 404
    )
    assert (
        env.client.delete(f"/api/v1/history/{conversation_a}", headers=headers(token_b)).status_code
        == 404
    )
    rating = {"answer_id": answer_a, "rating": "up"}
    assert (
        env.client.post("/api/v1/feedback", json=rating, headers=headers(token_b)).status_code
        == 404
    )
    assert (
        env.client.post(
            "/api/v1/saved", json={"answer_id": answer_a}, headers=headers(token_b)
        ).status_code
        == 404
    )
    assert env.client.get("/api/v1/saved", headers=headers(token_b)).json()["items"] == []
    assert (
        env.client.delete(f"/api/v1/saved/{answer_a}", headers=headers(token_b)).status_code == 404
    )

    env.client.put(
        "/api/v1/preferences",
        json={"theme": "dark", "default_mode": "local"},
        headers=headers(token_a),
    )
    prefs_b = env.client.get("/api/v1/preferences", headers=headers(token_b)).json()
    assert prefs_b["theme"] == "system"
    assert (
        env.client.get(f"/api/v1/history/{conversation_a}", headers=headers(token_a)).status_code
        == 200
    )


def test_the_same_account_sees_its_history_after_signing_in_again(env):
    email, token, _ = new_user(env)
    ask_as(env, token)
    again = env.client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["token"]
    assert len(env.client.get("/api/v1/history", headers=headers(again)).json()["items"]) == 1


def test_an_anonymous_visitor_is_not_an_account_and_cannot_use_session_routes(env):
    visitor = anonymous_visitor(env)
    from app.visitor import issue_token

    anon = issue_token(visitor, VISITOR_SECRET, 3600)
    assert env.client.get("/api/v1/auth/me", headers=headers(anon)).status_code == 401
    assert env.client.get("/api/v1/history", headers=headers(anon)).status_code == 200


def test_clearing_my_data_keeps_the_account_working(env):
    email, token, _ = new_user(env)
    ask_as(env, token)
    assert env.client.delete("/api/v1/me", headers=headers(token)).status_code == 200
    assert env.client.get("/api/v1/history", headers=headers(token)).json()["items"] == []
    assert env.client.get("/api/v1/auth/me", headers=headers(token)).status_code == 200
    again = env.client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert again.status_code == 200


# ---------------------------------------------------------------- claiming and deleting


def test_claiming_anonymous_history_works_once_and_needs_the_password(env):
    from app.visitor import issue_token

    _, token, _ = new_user(env)
    visitor = anonymous_visitor(env)
    anon = issue_token(visitor, VISITOR_SECRET, 3600)
    ask_as(env, anon)
    body = {"password": PASSWORD, "anonymous_token": anon}
    wrong = env.client.post(
        "/api/v1/auth/claim", headers=headers(token), json={**body, "password": "x" * 12}
    )
    assert wrong.status_code == 401
    done = env.client.post("/api/v1/auth/claim", headers=headers(token), json=body)
    assert done.status_code == 200 and done.json()["detail"]["conversations"] == 1
    assert len(env.client.get("/api/v1/history", headers=headers(token)).json()["items"]) == 1
    again = env.client.post("/api/v1/auth/claim", headers=headers(token), json=body)
    assert again.status_code == 404


def test_a_second_account_cannot_claim_what_the_first_already_claimed(env):
    from app.visitor import issue_token

    _, first, _ = new_user(env)
    _, second, _ = new_user(env)
    visitor = anonymous_visitor(env)
    anon = issue_token(visitor, VISITOR_SECRET, 3600)
    body = {"password": PASSWORD, "anonymous_token": anon}
    assert (
        env.client.post("/api/v1/auth/claim", headers=headers(first), json=body).status_code == 200
    )
    assert (
        env.client.post("/api/v1/auth/claim", headers=headers(second), json=body).status_code == 404
    )


def test_a_forged_anonymous_token_claims_nothing(env):
    _, token, _ = new_user(env)
    body = {"password": PASSWORD, "anonymous_token": f"v1.{uuid.uuid4()}.9999999999.deadbeef"}
    assert (
        env.client.post("/api/v1/auth/claim", headers=headers(token), json=body).status_code == 404
    )


def test_deleting_the_account_removes_everything_and_ends_the_session(env):
    email, token, _ = new_user(env)
    ask_as(env, token)
    with env.engine.begin() as conn:
        user_id = conn.execute(
            text("SELECT id FROM users WHERE email = :e"), {"e": email}
        ).scalar_one()
    wrong = env.client.request(
        "DELETE", "/api/v1/auth/account", headers=headers(token), json={"password": "x" * 12}
    )
    assert wrong.status_code == 401
    done = env.client.request(
        "DELETE", "/api/v1/auth/account", headers=headers(token), json={"password": PASSWORD}
    )
    assert done.status_code == 200 and done.json()["detail"]["conversations"] == 1
    with env.engine.begin() as conn:
        left = {
            table: conn.execute(
                text(f"SELECT count(*) FROM {table} WHERE user_id = :u"),  # noqa: S608
                {"u": user_id},
            ).scalar_one()
            for table in (
                "sessions",
                "recovery_codes",
                "reset_tokens",
                "visitors",
                "admin_audit_log",
            )
        }
        users = conn.execute(
            text("SELECT count(*) FROM users WHERE email = :e"), {"e": email}
        ).scalar_one()
    assert users == 0 and all(count == 0 for count in left.values())
    assert env.client.get("/api/v1/auth/me", headers=headers(token)).status_code == 401
    login = env.client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 401


def test_sign_in_events_are_audited_without_the_email(env):
    email, token, codes = new_user(env)
    env.client.post("/api/v1/auth/login", json={"email": email, "password": WRONG})
    env.client.post(
        "/api/v1/auth/reset",
        json={"email": email, "recovery_code": codes[0], "new_password": OTHER},
    )
    link_for(env, email)
    with env.engine.begin() as conn:
        rows = conn.execute(
            text("SELECT action, target FROM admin_audit_log a JOIN users u ON u.id = a.user_id "
                 "WHERE u.email = :e"),
            {"e": email},
        ).all()  # fmt: skip
    actions = {r[0] for r in rows}
    assert {"signup", "login_failed", "password_reset_code", "reset_link_issued"} <= actions
    assert all(email not in (r[1] or "") for r in rows)
