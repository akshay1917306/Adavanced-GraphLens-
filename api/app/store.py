"""Saving answers, feedback and reading the run status, in the tables that already exist.

There is no sign-in yet (Phase 6), so every request belongs to one anonymous local visitor.
All SQL is parameterised; no text from a question or an answer is ever put into a query string.
"""

from functools import lru_cache
from uuid import UUID

from sqlalchemy import Engine, create_engine, text

from app.config import get_settings
from app.schemas import Answer

LOCAL_VISITOR = "local-demo"  # marker in visitors.ip_hash for the single local visitor
TITLE_CHARS = 80


class Store:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def _visitor_id(self, conn) -> UUID:
        row = conn.execute(
            text("SELECT id FROM visitors WHERE ip_hash = :marker ORDER BY first_seen_at LIMIT 1"),
            {"marker": LOCAL_VISITOR},
        ).first()
        if row:
            conn.execute(
                text("UPDATE visitors SET last_seen_at = now() WHERE id = :id"), {"id": row[0]}
            )
            return row[0]
        return conn.execute(
            text("INSERT INTO visitors (ip_hash) VALUES (:marker) RETURNING id"),
            {"marker": LOCAL_VISITOR},
        ).scalar_one()

    def save_answer(self, question: str, answer: Answer, index_version: str) -> str:
        """Store the question, the answer, its metadata and its citations. Returns the answer id."""
        with self._engine.begin() as conn:
            visitor = self._visitor_id(conn)
            conversation = conn.execute(
                text("INSERT INTO conversations (visitor_id, title) VALUES (:v, :t) RETURNING id"),
                {"v": visitor, "t": question[:TITLE_CHARS]},
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
        self, answer_id: UUID, rating: str, reason: str | None, comment: str | None
    ) -> bool:
        """Store or replace the visitor's rating. False when there is no such answer."""
        with self._engine.begin() as conn:
            known = conn.execute(
                text("SELECT 1 FROM messages WHERE id = :id AND role = 'assistant'"),
                {"id": answer_id},
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
                    "v": self._visitor_id(conn),
                    "rating": rating,
                    "reason": reason,
                    "comment": comment,
                },
            )
        return True

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
    engine = create_engine(get_settings().database_url.get_secret_value(), pool_pre_ping=True)
    return Store(engine)
