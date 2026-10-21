import shutil

import pytest
from sqlalchemy import create_engine, text

from app.fixtures import (
    DEFAULT_FIXTURE_DIR,
    DEFAULT_ONTOLOGY,
    check_fixtures,
    load_fixtures,
)


def test_all_ten_fixture_documents_are_valid():
    docs, problems = check_fixtures(DEFAULT_FIXTURE_DIR)
    assert problems == []
    assert len(docs) == 10
    assert {d.format for d in docs} == {"markdown", "text", "html"}


def test_injection_fixture_is_low_trust():
    docs, _ = check_fixtures(DEFAULT_FIXTURE_DIR)
    by_file = {d.file: d for d in docs}
    assert by_file["docs/p10_untrusted_note.md"].trust_level == "low"


def test_changed_file_is_detected(tmp_path):
    copy = tmp_path / "fixture"
    shutil.copytree(DEFAULT_FIXTURE_DIR, copy)
    (copy / "docs" / "p01_lattice_rank.md").write_text("tampered", encoding="utf-8")
    _, problems = check_fixtures(copy)
    assert problems == ["docs/p01_lattice_rank.md: hash mismatch (file changed?)"]


def test_missing_file_is_detected(tmp_path):
    copy = tmp_path / "fixture"
    shutil.copytree(DEFAULT_FIXTURE_DIR, copy)
    (copy / "docs" / "p05_denselite.md").unlink()
    _, problems = check_fixtures(copy)
    assert problems == ["docs/p05_denselite.md: file missing"]


@pytest.mark.integration
def test_load_is_idempotent(migrated_db):
    engine = create_engine(migrated_db)
    try:
        assert load_fixtures(engine, DEFAULT_FIXTURE_DIR, DEFAULT_ONTOLOGY) == 10
        assert load_fixtures(engine, DEFAULT_FIXTURE_DIR, DEFAULT_ONTOLOGY) == 10  # no duplicates
        with engine.connect() as conn:
            low = conn.execute(
                text("SELECT count(*) FROM documents WHERE trust_level = 'low'")
            ).scalar_one()
        assert low == 1
    finally:
        engine.dispose()
