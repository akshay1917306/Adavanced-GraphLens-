"""Integration test of the store on a disposable Postgres (set DATABASE_URL; skipped otherwise)."""

import uuid

import pytest
from sqlalchemy import create_engine, text

from app.schemas import Answer, Citation
from app.store import Store

pytestmark = pytest.mark.integration


@pytest.fixture
def store(migrated_db):
    engine = create_engine(migrated_db)
    yield Store(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM conversations"))
        conn.execute(text("DELETE FROM visitors"))
    engine.dispose()


def _answer():
    cite = Citation(label="T1", kind="text_unit", title="P", text="passage", ref_id="u_1")
    return Answer(mode="local", status="answered", text="X [T1].", citations=[cite, cite],
                  check_status="verified", model="m", cost_usd=0.004, latency_ms=5)  # fmt: skip


def test_answer_trace_and_feedback_round_trip(store):
    me = store.create_visitor()
    answer_id = store.save_answer(me, "What is X?", _answer(), "idx-test")
    assert store.save_feedback(me, uuid.UUID(answer_id), "up", None, None)
    assert store.save_feedback(me, uuid.UUID(answer_id), "down", "other", "changed my mind")
    with store._engine.connect() as conn:
        rows = conn.execute(text("SELECT rating FROM feedback")).all()
        traces = conn.execute(text("SELECT ref_id, cited FROM retrieval_traces")).all()
        meta = conn.execute(
            text("SELECT mode_used, citation_status, refused FROM answer_meta")
        ).one()
        visitors = conn.execute(text("SELECT count(*) FROM visitors")).scalar_one()
    assert rows == [("down",)]  # one rating per visitor and answer: the second replaced the first
    assert traces == [("u_1", True)]  # a repeated citation is stored once
    assert tuple(meta) == ("local", "verified", False)
    assert visitors == 1  # the one visitor made above
    assert store.status()["answers_saved"] == 1


def test_feedback_for_an_unknown_answer_is_refused(store):
    me = store.create_visitor()
    assert store.save_feedback(me, uuid.uuid4(), "up", None, None) is False


def test_a_visitor_cannot_rate_someone_elses_answer(store):
    owner, other = store.create_visitor(), store.create_visitor()
    answer_id = uuid.UUID(store.save_answer(owner, "Q?", _answer(), "idx-test"))
    assert store.save_feedback(other, answer_id, "down", None, None) is False
    with store._engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM feedback")).scalar_one() == 0
    assert store.save_feedback(owner, answer_id, "up", None, None) is True


def test_unknown_visitor_does_not_exist(store):
    assert store.visitor_exists(uuid.uuid4()) is False
    assert store.visitor_exists(store.create_visitor()) is True
