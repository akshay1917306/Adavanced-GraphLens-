"""Integration test: the first migration creates (and removes) every blueprint table.

Needs a disposable Postgres. Set DATABASE_URL to run it; otherwise it is skipped.
WARNING: this test drops all tables in that database.
"""

import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

pytestmark = pytest.mark.integration

API_DIR = Path(__file__).resolve().parents[1]
DATABASE_URL = os.environ.get("DATABASE_URL")

BLUEPRINT_TABLES = {
    "ontologies", "corpora", "documents", "text_units",
    "index_runs", "run_stages", "extraction_cache", "resolution_decisions", "quality_checks",
    "users", "visitors", "preferences",
    "conversations", "messages", "retrieval_traces", "answer_meta",
    "feedback", "saved_answers", "admin_audit_log",
    "eval_sets", "eval_questions", "eval_runs", "eval_results",
}  # fmt: skip
ACCOUNT_TABLES = {"sessions", "recovery_codes", "reset_tokens"}  # added by 0002 (Phase 8)


def alembic(*args: str) -> None:
    subprocess.run(["alembic", *args], cwd=API_DIR, check=True)  # noqa: S603, S607


def table_names() -> set[str]:
    engine = create_engine(DATABASE_URL)
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


@pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL not set")
def test_upgrade_creates_all_tables_and_downgrade_removes_them():
    alembic("downgrade", "base")
    alembic("upgrade", "head")
    assert table_names() == BLUEPRINT_TABLES | ACCOUNT_TABLES
    alembic("downgrade", "0001")  # the accounts step alone can be undone
    assert table_names() == BLUEPRINT_TABLES
    alembic("upgrade", "head")
    alembic("downgrade", "base")
    assert table_names() == set()
    alembic("upgrade", "head")  # leave the database migrated for later tests
