"""User data on a disposable Postgres (set DATABASE_URL; skipped otherwise).

Every test has two visitors: the second one must never see or change the first one's rows.
"""

import uuid

import pytest
from sqlalchemy import create_engine, text

from app.schemas import Answer, Citation
from app.store import Store

pytestmark = pytest.mark.integration

TABLES = [
    "conversations",
    "messages",
    "answer_meta",
    "retrieval_traces",
    "feedback",
    "saved_answers",
]


@pytest.fixture
def store(migrated_db):
    engine = create_engine(migrated_db)
    yield Store(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM visitors"))
    engine.dispose()


def _answer(text_="X [T1]."):
    cite = Citation(label="T1", kind="text_unit", title="P", text="passage", ref_id="u_1")
    return Answer(mode="local", status="answered", text=text_, citations=[cite],
                  check_status="verified", model="m")  # fmt: skip


def _count(store, table, where="", **params):
    with store._engine.connect() as conn:
        sql = f"SELECT count(*) FROM {table} {where}"  # noqa: S608 (fixed table names in tests)
        return conn.execute(text(sql), params).scalar_one()


def test_history_is_private_and_newest_first(store):
    me, other = store.create_visitor(), store.create_visitor()
    store.save_answer(me, "first?", _answer(), "iv")
    store.save_answer(me, "second?", _answer(), "iv")
    store.save_answer(other, "not mine?", _answer(), "iv")
    mine = store.list_history(me)
    assert [i["title"] for i in mine] == ["second?", "first?"]
    assert mine[0]["mode"] == "local"
    assert mine[0]["check_status"] == "verified"
    assert [i["title"] for i in store.list_history(other)] == ["not mine?"]
    assert store.list_history(store.create_visitor()) == []


def test_a_conversation_can_only_be_opened_by_its_owner(store):
    me, other = store.create_visitor(), store.create_visitor()
    answer_id = uuid.UUID(store.save_answer(me, "Q?", _answer(), "iv"))
    store.save_feedback(me, answer_id, "up", None, None)
    conversation = store.list_history(me)[0]["conversation_id"]
    detail = store.get_conversation(me, conversation)
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["rating"] == "up"
    assert store.get_conversation(other, conversation) is None
    assert store.get_conversation(me, uuid.uuid4()) is None


def test_deleting_a_conversation_removes_everything_under_it(store):
    me, other = store.create_visitor(), store.create_visitor()
    answer_id = uuid.UUID(store.save_answer(me, "Q?", _answer(), "iv"))
    store.save_feedback(me, answer_id, "up", None, None)
    store.save_for_later(me, answer_id, "note")
    conversation = store.list_history(me)[0]["conversation_id"]
    assert store.delete_conversation(other, conversation) is False  # not theirs
    assert _count(store, "conversations") == 1
    assert store.delete_conversation(me, conversation) is True
    for table in TABLES:
        assert _count(store, table) == 0, table
    assert store.delete_conversation(me, conversation) is False  # already gone


def test_saved_answers_are_private(store):
    me, other = store.create_visitor(), store.create_visitor()
    answer_id = uuid.UUID(store.save_answer(me, "Q?", _answer("the answer"), "iv"))
    assert store.save_for_later(other, answer_id, "mine now") is False
    assert store.save_for_later(me, answer_id, "first note") is True
    assert store.save_for_later(me, answer_id, "changed note") is True  # one row per answer
    saved = store.list_saved(me)
    assert len(saved) == 1
    assert saved[0]["note"] == "changed note"
    assert saved[0]["answer_text"] == "the answer"
    assert store.list_saved(other) == []
    assert store.delete_saved(other, answer_id) is False
    assert store.delete_saved(me, answer_id) is True
    assert store.list_saved(me) == []


def test_preferences_default_update_and_stay_separate(store):
    me, other = store.create_visitor(), store.create_visitor()
    assert store.get_preferences(me) == {
        "theme": "system",
        "default_mode": "auto",
        "evidence_panel_open": True,
    }
    store.set_preferences(me, "dark", "local", False)
    store.set_preferences(me, "light", "global", True)
    assert store.get_preferences(me) == {
        "theme": "light",
        "default_mode": "global",
        "evidence_panel_open": True,
    }
    assert store.get_preferences(other)["theme"] == "system"


def test_deleting_all_my_data_leaves_nothing_of_mine_and_nothing_else_changes(store):
    me, other = store.create_visitor(), store.create_visitor()
    mine = uuid.UUID(store.save_answer(me, "mine?", _answer(), "iv"))
    store.save_answer(me, "mine too?", _answer(), "iv")
    store.save_feedback(me, mine, "down", "other", "no")
    store.save_for_later(me, mine, "n")
    store.set_preferences(me, "dark", "local", False)
    theirs = uuid.UUID(store.save_answer(other, "theirs?", _answer(), "iv"))
    store.save_feedback(other, theirs, "up", None, None)

    counts = store.delete_visitor_data(me)
    assert counts == {"conversations": 2, "saved_answers": 1, "ratings": 1}
    assert store.visitor_exists(me) is False
    for table in ("conversations", "feedback", "saved_answers", "preferences"):
        assert (
            _count(
                store,
                table,
                "WHERE visitor_id = :v" if table != "conversations" else "WHERE visitor_id = :v",
                v=me,
            )
            == 0
        )
    assert _count(store, "messages") == 2  # only the other visitor's question and answer
    assert _count(store, "answer_meta") == 1
    assert _count(store, "retrieval_traces") == 1
    assert [i["title"] for i in store.list_history(other)] == ["theirs?"]
    assert store.visitor_exists(other) is True
