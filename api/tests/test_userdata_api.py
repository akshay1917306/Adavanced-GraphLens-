"""The user-data routes with a fake store: wiring, validation, 404s, and deny by default."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app import main
from app import visitor as visitor_module
from app.config import Settings

ME = UUID("00000000-0000-0000-0000-0000000000aa")
NOW = datetime(2026, 10, 27, tzinfo=UTC)
CONV = uuid4()


class FakeStore:
    def __init__(self, owns: bool = True):
        self.owns = owns
        self.calls: list[tuple] = []

    def visitor_exists(self, visitor_id):
        return (
            False  # only used by the real get_visitor: no stored visitor, so everything is refused
        )

    def list_history(self, visitor_id, limit=50):
        self.calls.append(("history", visitor_id, limit))
        return [{"conversation_id": CONV, "title": "Q?", "created_at": NOW}]

    def get_conversation(self, visitor_id, conversation_id):
        if not self.owns:
            return None
        return {
            "conversation_id": conversation_id,
            "title": "Q?",
            "created_at": NOW,
            "messages": [{"id": uuid4(), "role": "user", "content": "Q?", "created_at": NOW}],
        }

    def delete_conversation(self, visitor_id, conversation_id):
        self.calls.append(("delete", visitor_id, conversation_id))
        return self.owns

    def delete_visitor_data(self, visitor_id):
        self.calls.append(("delete_all", visitor_id))
        return {"conversations": 2, "saved_answers": 1, "ratings": 3}

    def save_for_later(self, visitor_id, answer_id, note):
        self.calls.append(("save", visitor_id, answer_id, note))
        return self.owns

    def list_saved(self, visitor_id):
        return []

    def delete_saved(self, visitor_id, answer_id):
        return self.owns

    def get_preferences(self, visitor_id):
        return {"theme": "system", "default_mode": "auto", "evidence_panel_open": True}

    def set_preferences(self, visitor_id, theme, default_mode, panel_open):
        self.calls.append(("prefs", visitor_id, theme, default_mode, panel_open))


@pytest.fixture
def make(monkeypatch):
    def build(store, signed_in=True):
        monkeypatch.setattr(main, "get_settings", lambda: Settings(visitor_token_secret="s"))
        monkeypatch.setattr(
            visitor_module, "get_settings", lambda: Settings(visitor_token_secret="s")
        )
        main.app.dependency_overrides[main.get_store] = lambda: store
        if signed_in:
            main.app.dependency_overrides[visitor_module.get_visitor] = lambda: ME
        return TestClient(main.app, raise_server_exceptions=False)

    yield build
    main.app.dependency_overrides.clear()


def test_history_lists_the_visitors_conversations(make):
    store = FakeStore()
    body = make(store).get("/api/v1/history?limit=5").json()
    assert body["items"][0]["title"] == "Q?"
    assert store.calls == [("history", ME, 5)]


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "limit=abc"])
def test_history_limit_is_bounded(make, query):
    assert make(FakeStore()).get(f"/api/v1/history?{query}").status_code == 422


def test_opening_someone_elses_conversation_is_not_found(make):
    response = make(FakeStore(owns=False)).get(f"/api/v1/history/{CONV}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_a_bad_id_is_rejected_without_echo(make):
    response = make(FakeStore()).get("/api/v1/history/not-a-uuid")
    assert response.status_code == 422
    assert "not-a-uuid" not in response.text


def test_delete_one_and_not_found(make):
    assert make(FakeStore()).delete(f"/api/v1/history/{CONV}").json() == {"deleted": True}
    assert make(FakeStore(owns=False)).delete(f"/api/v1/history/{CONV}").status_code == 404


def test_delete_all_reports_what_was_removed(make):
    store = FakeStore()
    body = make(store).delete("/api/v1/me").json()
    assert body == {"conversations": 2, "saved_answers": 1, "ratings": 3}
    assert store.calls == [("delete_all", ME)]


def test_save_validates_and_checks_ownership(make):
    answer = str(uuid4())
    assert make(FakeStore()).post(
        "/api/v1/saved", json={"answer_id": answer, "note": "n"}
    ).json() == {"saved": True}
    assert (
        make(FakeStore(owns=False)).post("/api/v1/saved", json={"answer_id": answer}).status_code
        == 404
    )
    too_long = {"answer_id": answer, "note": "x" * 501}
    assert make(FakeStore()).post("/api/v1/saved", json=too_long).status_code == 422
    assert make(FakeStore()).delete(f"/api/v1/saved/{answer}").json() == {"deleted": True}
    assert make(FakeStore(owns=False)).delete(f"/api/v1/saved/{answer}").status_code == 404


def test_preferences_round_trip_and_validation(make):
    store = FakeStore()
    client = make(store)
    assert client.get("/api/v1/preferences").json()["theme"] == "system"
    new = {"theme": "dark", "default_mode": "local", "evidence_panel_open": False}
    assert client.put("/api/v1/preferences", json=new).json() == new
    assert store.calls == [("prefs", ME, "dark", "local", False)]
    for bad in ({"theme": "pink"}, {"default_mode": "sql"}, {"theme": "dark", "extra": 1}):
        assert client.put("/api/v1/preferences", json=bad).status_code == 422


ROUTES = [
    ("get", "/api/v1/history"),
    ("get", f"/api/v1/history/{CONV}"),
    ("delete", f"/api/v1/history/{CONV}"),
    ("delete", "/api/v1/me"),
    ("get", "/api/v1/saved"),
    ("post", "/api/v1/saved"),
    ("delete", f"/api/v1/saved/{uuid4()}"),
    ("get", "/api/v1/preferences"),
    ("put", "/api/v1/preferences"),
]


@pytest.mark.parametrize(("method", "path"), ROUTES)
def test_every_route_refuses_a_request_without_a_valid_visitor(make, method, path):
    client = make(FakeStore(), signed_in=False)
    body = {"answer_id": str(uuid4())} if method in ("post", "put") else None
    response = getattr(client, method)(
        path, headers={"X-Visitor-Token": "forged"}, **({"json": body} if body else {})
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "visitor_required"
