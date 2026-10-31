"""Saving answers, feedback and reading the run status, in the tables that already exist.

Every row belongs to an anonymous visitor (signed token, see visitor.py); there is no sign-in.
All SQL is parameterised; no text from a question or an answer is ever put into a query string.
"""

from functools import lru_cache
from uuid import UUID

from sqlalchemy import Engine, create_engine, text

from app.config import get_settings
from app.schemas import Answer

TITLE_CHARS = 80


class Store:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_visitor(self) -> UUID:
        with self._engine.begin() as conn:
            return conn.execute(
                text("INSERT INTO visitors DEFAULT VALUES RETURNING id")
            ).scalar_one()

    def visitor_exists(self, visitor_id: UUID) -> bool:
        with self._engine.begin() as conn:
            found = conn.execute(
                text("UPDATE visitors SET last_seen_at = now() WHERE id = :id RETURNING id"),
                {"id": visitor_id},
            ).first()
        return found is not None

    def save_answer(
        self, visitor_id: UUID, question: str, answer: Answer, index_version: str
    ) -> str:
        """Store the question, the answer, its metadata and its citations. Returns the answer id."""
        with self._engine.begin() as conn:
            conversation = conn.execute(
                text("INSERT INTO conversations (visitor_id, title) VALUES (:v, :t) RETURNING id"),
                {"v": visitor_id, "t": question[:TITLE_CHARS]},
            ).scalar_one()
            message = (
                "INSERT INTO messages (conversation_id, role, content, mode_requested) "
                "VALUES (:c, :role, :content, 'auto') RETURNING id"
            )
            conn.execute(text(message), {"c": conversation, "role": "user", "content": question})
            answer_id = conn.execute(
                text(message),
                {
                    "c": conversation,
                    "role": "assistant",
                    "content": answer.text or answer.message or "",
                },
            ).scalar_one()
            conn.execute(
                text(
                    "INSERT INTO answer_meta (message_id, mode_used, model, index_version, "
                    "latency_ms, cost_usd, citation_status, refused) VALUES "
                    "(:m, :mode, :model, :iv, :lat, :cost, :check, :refused)"
                ),
                {
                    "m": answer_id,
                    "mode": answer.mode,
                    "model": answer.model or "unknown",
                    "iv": index_version,
                    "lat": answer.latency_ms,
                    "cost": answer.cost_usd,
                    "check": answer.check_status,
                    "refused": answer.status == "refused",
                },
            )
            for rank, citation in enumerate(answer.citations):
                conn.execute(
                    text(
                        "INSERT INTO retrieval_traces (message_id, kind, ref_id, rank, cited) "
                        "VALUES (:m, :kind, :ref, :rank, true) ON CONFLICT DO NOTHING"
                    ),
                    {
                        "m": answer_id,
                        "kind": citation.kind,
                        "ref": citation.ref_id or citation.label,
                        "rank": rank,
                    },
                )
        return str(answer_id)

    def save_feedback(
        self,
        visitor_id: UUID,
        answer_id: UUID,
        rating: str,
        reason: str | None,
        comment: str | None,
    ) -> bool:
        """Store or replace the visitor's rating. False when the answer is not this visitor's."""
        with self._engine.begin() as conn:
            known = conn.execute(
                text(
                    "SELECT 1 FROM messages m JOIN conversations c ON c.id = m.conversation_id "
                    "WHERE m.id = :id AND m.role = 'assistant' AND c.visitor_id = :v "
                    "AND c.deleted_at IS NULL"
                ),
                {"id": answer_id, "v": visitor_id},
            ).first()
            if not known:
                return False
            conn.execute(
                text(
                    "INSERT INTO feedback (message_id, visitor_id, rating, reason, comment) "
                    "VALUES (:m, :v, :rating, :reason, :comment) "
                    "ON CONFLICT (message_id, visitor_id) DO UPDATE SET "
                    "rating = EXCLUDED.rating, reason = EXCLUDED.reason, "
                    "comment = EXCLUDED.comment, created_at = now()"
                ),
                {
                    "m": answer_id,
                    "v": visitor_id,
                    "rating": rating,
                    "reason": reason,
                    "comment": comment,
                },
            )
        return True

    # ---- history, saved answers, preferences: every query is limited to one visitor

    def list_history(self, visitor_id: UUID, limit: int = 50) -> list[dict]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT c.id AS conversation_id, c.title, c.created_at, "
                    "m.id AS answer_id, a.mode_used AS mode, a.citation_status AS check_status, "
                    "coalesce(a.refused, false) AS refused FROM conversations c "
                    "LEFT JOIN LATERAL (SELECT id FROM messages WHERE conversation_id = c.id "
                    "AND role = 'assistant' ORDER BY created_at DESC LIMIT 1) m ON true "
                    "LEFT JOIN answer_meta a ON a.message_id = m.id "
                    "WHERE c.visitor_id = :v AND c.deleted_at IS NULL "
                    "ORDER BY c.created_at DESC LIMIT :limit"
                ),
                {"v": visitor_id, "limit": limit},
            ).mappings().all()  # fmt: skip
        return [dict(r) for r in rows]

    def get_conversation(self, visitor_id: UUID, conversation_id: UUID) -> dict | None:
        """One conversation with its messages, or None when it is not this visitor's."""
        with self._engine.connect() as conn:
            head = conn.execute(
                text(
                    "SELECT id AS conversation_id, title, created_at FROM conversations "
                    "WHERE id = :id AND visitor_id = :v AND deleted_at IS NULL"
                ),
                {"id": conversation_id, "v": visitor_id},
            ).mappings().first()  # fmt: skip
            if head is None:
                return None
            messages = conn.execute(
                text(
                    "SELECT m.id, m.role, m.content, m.created_at, a.mode_used AS mode, "
                    "a.citation_status AS check_status, coalesce(a.refused, false) AS refused, "
                    "f.rating FROM messages m LEFT JOIN answer_meta a ON a.message_id = m.id "
                    "LEFT JOIN feedback f ON f.message_id = m.id AND f.visitor_id = :v "
                    "WHERE m.conversation_id = :id ORDER BY m.created_at, m.role DESC"
                ),
                {"id": conversation_id, "v": visitor_id},
            ).mappings().all()  # fmt: skip
        return {**head, "messages": [dict(m) for m in messages]}

    def delete_conversation(self, visitor_id: UUID, conversation_id: UUID) -> bool:
        """Really delete one conversation and everything under it. False when it is not theirs."""
        with self._engine.begin() as conn:
            gone = conn.execute(
                text("DELETE FROM conversations WHERE id = :id AND visitor_id = :v RETURNING id"),
                {"id": conversation_id, "v": visitor_id},
            ).first()
        return gone is not None

    def delete_visitor_data(self, visitor_id: UUID) -> dict:
        """Delete the visitor and, by cascade, all their conversations, ratings, saved answers
        and preferences. The counts are read first so the screen can say what was removed."""
        with self._engine.begin() as conn:
            counts = conn.execute(
                text(
                    "SELECT (SELECT count(*) FROM conversations WHERE visitor_id = :v) "
                    "AS conversations, (SELECT count(*) FROM saved_answers WHERE visitor_id = :v) "
                    "AS saved_answers, (SELECT count(*) FROM feedback WHERE visitor_id = :v) "
                    "AS ratings"
                ),
                {"v": visitor_id},
            ).mappings().one()  # fmt: skip
            signed_in = conn.execute(
                text("SELECT user_id FROM visitors WHERE id = :v"), {"v": visitor_id}
            ).scalar()
            if signed_in is None:
                conn.execute(text("DELETE FROM visitors WHERE id = :v"), {"v": visitor_id})
            else:  # the home visitor of an account stays; only its data goes
                for table in ("conversations", "saved_answers", "feedback", "preferences"):
                    conn.execute(
                        text(f"DELETE FROM {table} WHERE visitor_id = :v"),  # noqa: S608
                        {"v": visitor_id},
                    )
        return dict(counts)

    def _owns_answer(self, conn, visitor_id: UUID, answer_id: UUID) -> bool:
        return (
            conn.execute(
                text(
                    "SELECT 1 FROM messages m JOIN conversations c ON c.id = m.conversation_id "
                    "WHERE m.id = :id AND m.role = 'assistant' AND c.visitor_id = :v "
                    "AND c.deleted_at IS NULL"
                ),
                {"id": answer_id, "v": visitor_id},
            ).first()
            is not None
        )

    def save_for_later(self, visitor_id: UUID, answer_id: UUID, note: str | None) -> bool:
        with self._engine.begin() as conn:
            if not self._owns_answer(conn, visitor_id, answer_id):
                return False
            conn.execute(
                text(
                    "INSERT INTO saved_answers (visitor_id, message_id, note) VALUES (:v, :m, :n) "
                    "ON CONFLICT (visitor_id, message_id) DO UPDATE SET note = EXCLUDED.note"
                ),
                {"v": visitor_id, "m": answer_id, "n": note},
            )
        return True

    def list_saved(self, visitor_id: UUID) -> list[dict]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT s.message_id AS answer_id, s.note, c.title, m.content AS answer_text, "
                    "s.created_at AS saved_at FROM saved_answers s "
                    "JOIN messages m ON m.id = s.message_id "
                    "JOIN conversations c ON c.id = m.conversation_id "
                    "WHERE s.visitor_id = :v ORDER BY s.created_at DESC"
                ),
                {"v": visitor_id},
            ).mappings().all()  # fmt: skip
        return [dict(r) for r in rows]

    def delete_saved(self, visitor_id: UUID, answer_id: UUID) -> bool:
        with self._engine.begin() as conn:
            gone = conn.execute(
                text(
                    "DELETE FROM saved_answers WHERE visitor_id = :v AND message_id = :m "
                    "RETURNING message_id"
                ),
                {"v": visitor_id, "m": answer_id},
            ).first()
        return gone is not None

    def get_preferences(self, visitor_id: UUID) -> dict:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT theme, default_mode, evidence_panel_open FROM preferences "
                    "WHERE visitor_id = :v"
                ),
                {"v": visitor_id},
            ).mappings().first()  # fmt: skip
        return (
            dict(row)
            if row
            else {"theme": "system", "default_mode": "auto", "evidence_panel_open": True}
        )

    def set_preferences(
        self, visitor_id: UUID, theme: str, default_mode: str, panel_open: bool
    ) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO preferences "
                    "(visitor_id, theme, default_mode, evidence_panel_open) "
                    "VALUES (:v, :t, :m, :p) ON CONFLICT (visitor_id) DO UPDATE SET "
                    "theme = EXCLUDED.theme, default_mode = EXCLUDED.default_mode, "
                    "evidence_panel_open = EXCLUDED.evidence_panel_open, updated_at = now()"
                ),
                {"v": visitor_id, "t": theme, "m": default_mode, "p": panel_open},
            )

    def audit(self, action: str, target: str | None = None) -> None:
        """Write one row to the admin audit log (no user account exists yet, so no user id)."""
        with self._engine.begin() as conn:
            conn.execute(
                text("INSERT INTO admin_audit_log (action, target) VALUES (:a, :t)"),
                {"a": action, "t": target},
            )

    def status(self) -> dict:
        """Read-only summary: the latest index runs, the latest run's quality checks, counts."""
        with self._engine.connect() as conn:
            runs = conn.execute(
                text(
                    "SELECT id, index_version, status, cost_usd, finished_at, published_at "
                    "FROM index_runs ORDER BY coalesce(finished_at, started_at) DESC NULLS LAST "
                    "LIMIT 5"
                )
            ).mappings().all()  # fmt: skip
            checks = []
            if runs:
                checks = conn.execute(
                    text(
                        "SELECT check_name, value, threshold, passed FROM quality_checks "
                        "WHERE run_id = :run ORDER BY check_name"
                    ),
                    {"run": runs[0]["id"]},
                ).mappings().all()  # fmt: skip
            counts = conn.execute(
                text(
                    "SELECT (SELECT count(*) FROM messages WHERE role = 'assistant') AS answers, "
                    "(SELECT count(*) FROM feedback) AS feedback"
                )
            ).mappings().one()  # fmt: skip
        return {
            "runs": [
                {
                    "index_version": r["index_version"],
                    "status": r["status"],
                    "cost_usd": float(r["cost_usd"]),
                    "finished_at": r["finished_at"].isoformat() if r["finished_at"] else None,
                    "published_at": r["published_at"].isoformat() if r["published_at"] else None,
                }
                for r in runs
            ],
            "quality_checks": [
                {
                    "name": c["check_name"],
                    "value": float(c["value"]) if c["value"] is not None else None,
                    "threshold": float(c["threshold"]) if c["threshold"] is not None else None,
                    "passed": c["passed"],
                }
                for c in checks
            ],
            "answers_saved": counts["answers"],
            "feedback_saved": counts["feedback"],
        }


@lru_cache
def get_store() -> Store:
    engine = create_engine(
        get_settings().database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},  # a down database fails in 3 seconds, not 4 or more
    )
    return Store(engine)
