"""Initial schema from blueprint v1.0 section 4.4.

Revision ID: 0001
Revises:
Create Date: 2026-10-21
"""

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SQL_FILE = Path(__file__).with_suffix(".sql")

# Reverse dependency order, so foreign keys never block a drop.
TABLES = [
    "eval_results",
    "eval_runs",
    "eval_questions",
    "eval_sets",
    "admin_audit_log",
    "saved_answers",
    "feedback",
    "answer_meta",
    "retrieval_traces",
    "messages",
    "conversations",
    "preferences",
    "visitors",
    "users",
    "quality_checks",
    "resolution_decisions",
    "extraction_cache",
    "run_stages",
    "index_runs",
    "text_units",
    "documents",
    "corpora",
    "ontologies",
]


def upgrade() -> None:
    op.execute(SQL_FILE.read_text(encoding="utf-8"))


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table}")
