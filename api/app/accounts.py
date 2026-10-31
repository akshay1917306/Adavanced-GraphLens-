"""Accounts, sessions, recovery codes and reset tokens in Postgres (Phase 8, Part B).

An account owns exactly one "home visitor". A session resolves to that visitor id, so every route
that already works for an anonymous visitor works unchanged for a signed-in user, with the same
ownership checks. All SQL is parameterised. Nothing here stores a plain secret.
"""

from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from app.passwords import fast_hash, new_secret, same
from app.store import get_store

SESSION_PREFIX = "s1"
IDLE_DAYS = 30
ABSOLUTE_DAYS = 90
RESET_MINUTES = 30


class EmailTaken(Exception):
    """An account with this email already exists."""


class UserCapReached(Exception):
    """The owner's limit on the number of accounts is reached."""


@dataclass(frozen=True)
class SessionUser:
    session_id: UUID
    user_id: UUID
    email: str
    home_visitor_id: UUID


def session_token(session_id: UUID, secret: str) -> str:
    return f"{SESSION_PREFIX}.{session_id}.{secret}"


def split_session_token(token: str) -> tuple[UUID, str] | None:
    parts = (token or "").split(".")
    if len(parts) != 3 or parts[0] != SESSION_PREFIX or len(token) > 200:
        return None
    try:
        return UUID(parts[1]), parts[2]
    except ValueError:
        return None


class Accounts:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # ---- accounts -------------------------------------------------------------------------

    def find_user(self, email: str) -> dict | None:
        with self._engine.begin() as conn:
            row = (
                conn.execute(
                    text(
                        "SELECT id, email, password_hash, home_visitor_id FROM users "
                        "WHERE email = :e AND password_hash IS NOT NULL"
                    ),
                    {"e": email},
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

    def create_account(
        self, email: str, password_hash: str, code_hashes: list[str], max_users: int
    ) -> tuple[UUID, UUID]:
        """The account, its home visitor and its first recovery codes. Returns (user, visitor)."""
        try:
            with self._engine.begin() as conn:
                total = conn.execute(
                    text("SELECT count(*) FROM users WHERE password_hash IS NOT NULL")
                ).scalar_one()
                if total >= max_users:
                    raise UserCapReached
                visitor = conn.execute(
                    text("INSERT INTO visitors DEFAULT VALUES RETURNING id")
                ).scalar_one()
                user = conn.execute(
                    text(
                        "INSERT INTO users (email, password_hash, home_visitor_id) "
                        "VALUES (:e, :p, :v) RETURNING id"
                    ),
                    {"e": email, "p": password_hash, "v": visitor},
                ).scalar_one()
                conn.execute(
                    text("UPDATE visitors SET user_id = :u WHERE id = :v"),
                    {"u": user, "v": visitor},
                )
                self._add_codes(conn, user, code_hashes, batch=1)
                self._audit(conn, user, "signup")
        except IntegrityError as error:  # the unique email index
            raise EmailTaken from error
        return user, visitor

    def get_user(self, user_id: UUID) -> dict | None:
        with self._engine.begin() as conn:
            row = (
                conn.execute(
                    text(
                        "SELECT u.id, u.email, u.password_hash, u.created_at, "
                        "(SELECT count(*) FROM recovery_codes r WHERE r.user_id = u.id "
                        "AND r.used_at IS NULL) AS unused_codes FROM users u WHERE u.id = :u"
                    ),
                    {"u": user_id},
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

    def set_password_hash(self, user_id: UUID, password_hash: str) -> None:
        """Only for upgrading an old hash after a correct sign-in."""
        with self._engine.begin() as conn:
            conn.execute(
                text("UPDATE users SET password_hash = :p WHERE id = :u"),
                {"p": password_hash, "u": user_id},
            )

    def delete_account(self, user_id: UUID) -> dict:
        """Delete the account, its visitors and by cascade all their rows. Audit rows stay, with
        the account id removed. Returns the counts that were removed."""
        with self._engine.begin() as conn:
            counts = (
                conn.execute(
                    text(
                        "SELECT (SELECT count(*) FROM conversations c JOIN visitors v ON "
                        "v.id = c.visitor_id WHERE v.user_id = :u) AS conversations, "
                        "(SELECT count(*) FROM saved_answers s JOIN visitors v ON "
                        "v.id = s.visitor_id WHERE v.user_id = :u) AS saved_answers, "
                        "(SELECT count(*) FROM feedback f JOIN visitors v ON "
                        "v.id = f.visitor_id WHERE v.user_id = :u) AS ratings"
                    ),
                    {"u": user_id},
                )
                .mappings()
                .one()
            )
            conn.execute(
                text("UPDATE admin_audit_log SET user_id = NULL WHERE user_id = :u"),
                {"u": user_id},
            )
            conn.execute(text("DELETE FROM visitors WHERE user_id = :u"), {"u": user_id})
            conn.execute(text("DELETE FROM users WHERE id = :u"), {"u": user_id})
            self._audit(conn, None, "account_deleted")
        return dict(counts)

    # ---- sessions -------------------------------------------------------------------------

    def create_session(self, user_id: UUID) -> str:
        """A new session; returns the token to give the browser (the secret is never stored)."""
        secret = new_secret()
        with self._engine.begin() as conn:
            session_id = self._new_session(conn, user_id, secret)
            conn.execute(
                text("UPDATE users SET last_login_at = now() WHERE id = :u"), {"u": user_id}
            )
        return session_token(session_id, secret)

    def _new_session(self, conn, user_id: UUID, secret: str) -> UUID:
        return conn.execute(
            text(
                "INSERT INTO sessions (user_id, secret_hash, expires_at) "
                "VALUES (:u, :h, now() + make_interval(days => :d)) RETURNING id"
            ),
            {"u": user_id, "h": fast_hash(secret), "d": ABSOLUTE_DAYS},
        ).scalar_one()

    def resolve_session(self, token: str) -> SessionUser | None:
        """The user of a genuine, unexpired, unrevoked session token, else None."""
        parts = split_session_token(token)
        if parts is None:
            return None
        session_id, secret = parts
        with self._engine.begin() as conn:
            row = (
                conn.execute(
                    text(
                        "SELECT s.id, s.secret_hash, u.id AS user_id, u.email, u.home_visitor_id "
                        "FROM sessions s JOIN users u ON u.id = s.user_id "
                        "WHERE s.id = :s AND s.revoked_at IS NULL AND s.expires_at > now() "
                        "AND s.last_used_at > now() - make_interval(days => :idle) "
                        "AND u.home_visitor_id IS NOT NULL"
                    ),
                    {"s": session_id, "idle": IDLE_DAYS},
                )
                .mappings()
                .first()
            )
            if row is None or not same(row["secret_hash"], fast_hash(secret)):
                return None
            conn.execute(
                text("UPDATE sessions SET last_used_at = now() WHERE id = :s"),
                {"s": session_id},
            )
        return SessionUser(row["id"], row["user_id"], row["email"], row["home_visitor_id"])

    def revoke_session(self, session_id: UUID) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("UPDATE sessions SET revoked_at = now() WHERE id = :s AND revoked_at IS NULL"),
                {"s": session_id},
            )

    def revoke_all_sessions(self, user_id: UUID) -> None:
        with self._engine.begin() as conn:
            self._revoke_all(conn, user_id)

    def _revoke_all(self, conn, user_id: UUID) -> None:
        conn.execute(
            text(
                "UPDATE sessions SET revoked_at = now() WHERE user_id = :u AND revoked_at IS NULL"
            ),
            {"u": user_id},
        )

    # ---- recovery codes -------------------------------------------------------------------

    def _add_codes(self, conn, user_id: UUID, code_hashes: list[str], batch: int) -> None:
        for code_hash in code_hashes:
            conn.execute(
                text("INSERT INTO recovery_codes (user_id, code_hash, batch) VALUES (:u, :h, :b)"),
                {"u": user_id, "h": code_hash, "b": batch},
            )

    def unused_codes(self, user_id: UUID) -> list[tuple[UUID, str]]:
        with self._engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, code_hash FROM recovery_codes "
                    "WHERE user_id = :u AND used_at IS NULL ORDER BY created_at"
                ),
                {"u": user_id},
            ).all()
        return [(r[0], r[1]) for r in rows]

    def replace_codes(self, user_id: UUID, code_hashes: list[str]) -> None:
        """A new set. Every unused code of the old set is burned."""
        with self._engine.begin() as conn:
            batch = conn.execute(
                text("SELECT COALESCE(max(batch), 0) + 1 FROM recovery_codes WHERE user_id = :u"),
                {"u": user_id},
            ).scalar_one()
            conn.execute(
                text(
                    "UPDATE recovery_codes SET used_at = now() "
                    "WHERE user_id = :u AND used_at IS NULL"
                ),
                {"u": user_id},
            )
            self._add_codes(conn, user_id, code_hashes, batch)
            self._audit(conn, user_id, "recovery_codes_new")

    # ---- reset ----------------------------------------------------------------------------

    def finish_reset(
        self, user_id: UUID, password_hash: str, how: str, code_id: UUID | None = None
    ) -> str:
        """Set the new password, burn the code used, end every session, start a new one.
        Returns the new session token. The code is burned first; if it was already used (a second
        request at the same moment) nothing changes and LookupError is raised."""
        secret = new_secret()
        with self._engine.begin() as conn:
            if code_id is not None:
                burned = conn.execute(
                    text(
                        "UPDATE recovery_codes SET used_at = now() "
                        "WHERE id = :c AND user_id = :u AND used_at IS NULL RETURNING id"
                    ),
                    {"c": code_id, "u": user_id},
                ).first()
                if burned is None:
                    raise LookupError
            conn.execute(
                text("UPDATE users SET password_hash = :p, last_login_at = now() WHERE id = :u"),
                {"p": password_hash, "u": user_id},
            )
            self._revoke_all(conn, user_id)
            session_id = self._new_session(conn, user_id, secret)
            self._audit(conn, user_id, f"password_reset_{how}")
        return session_token(session_id, secret)

    def issue_reset_token(self, user_id: UUID) -> str:
        """For the owner: a one-time token valid for 30 minutes. Older unused ones stop working."""
        token = new_secret()
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE reset_tokens SET used_at = now() WHERE user_id = :u AND used_at IS NULL"
                ),
                {"u": user_id},
            )
            conn.execute(
                text(
                    "INSERT INTO reset_tokens (user_id, token_hash, expires_at) "
                    "VALUES (:u, :h, now() + make_interval(mins => :m))"
                ),
                {"u": user_id, "h": fast_hash(token), "m": RESET_MINUTES},
            )
            self._audit(conn, user_id, "reset_link_issued")
        return token

    def take_reset_token(self, token: str) -> UUID | None:
        """Use a reset token (once). Returns the account id, or None when it is unknown, used or
        expired."""
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    "UPDATE reset_tokens SET used_at = now() WHERE token_hash = :h "
                    "AND used_at IS NULL AND expires_at > now() RETURNING user_id"
                ),
                {"h": fast_hash(token)},
            ).first()
        return row[0] if row else None

    # ---- claiming anonymous data ----------------------------------------------------------

    def claim(self, user_id: UUID, home_visitor: UUID, anonymous_visitor: UUID) -> dict | None:
        """Move an unclaimed anonymous visitor's rows into the account, once. None when that
        visitor does not exist, is already claimed, or is the account's own visitor."""
        if anonymous_visitor == home_visitor:
            return None
        with self._engine.begin() as conn:
            taken = conn.execute(
                text(
                    "UPDATE visitors SET user_id = :u WHERE id = :a AND user_id IS NULL "
                    "RETURNING id"
                ),
                {"u": user_id, "a": anonymous_visitor},
            ).first()
            if taken is None:
                return None
            moved = {}
            for table in ("conversations", "saved_answers", "feedback"):
                moved[table] = conn.execute(
                    text(f"UPDATE {table} SET visitor_id = :h WHERE visitor_id = :a"),  # noqa: S608
                    {"h": home_visitor, "a": anonymous_visitor},
                ).rowcount
            has_preferences = conn.execute(
                text("SELECT 1 FROM preferences WHERE visitor_id = :h"), {"h": home_visitor}
            ).first()
            if not has_preferences:
                conn.execute(
                    text("UPDATE preferences SET visitor_id = :h WHERE visitor_id = :a"),
                    {"h": home_visitor, "a": anonymous_visitor},
                )
            self._audit(conn, user_id, "anonymous_data_claimed")
        return moved

    # ---- audit ----------------------------------------------------------------------------

    def _audit(self, conn, user_id: UUID | None, action: str) -> None:
        conn.execute(
            text("INSERT INTO admin_audit_log (user_id, action) VALUES (:u, :a)"),
            {"u": user_id, "a": action},
        )

    def audit(self, user_id: UUID | None, action: str) -> None:
        with self._engine.begin() as conn:
            self._audit(conn, user_id, action)


@lru_cache
def get_accounts() -> Accounts:
    return Accounts(get_store()._engine)  # noqa: SLF001 (same engine, one connection pool)
