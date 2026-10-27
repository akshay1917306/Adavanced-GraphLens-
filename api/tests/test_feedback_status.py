"""Feedback and status endpoints with a fake store."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app import main
from app import visitor as visitor_module
from app.config import Settings

ANSWER_ID = "22222222-2222-2222-2222-222222222222"


class FakeStore:
    def __init__(self, known: bool = True):
        self.known = known
        self.calls = []

    def save_feedback(self, visitor_id, answer_id, rating, reason, comment):
        self.calls.append((str(answer_id), rating, reason, comment))
        return self.known

    def status(self):
        return {"runs": [], "quality_checks": [], "answers_saved": 0, "feedback_saved": 0}


@pytest.fixture
def make(monkeypatch):
    def build(store, key=""):
        main.app.dependency_overrides[main.get_store] = lambda: store
        main.app.dependency_overrides[visitor_module.get_visitor] = lambda: UUID(
            "00000000-0000-0000-0000-0000000000aa"
        )
        monkeypatch.setattr(main, "get_settings", lambda: Settings(admin_api_key=key))
        return TestClient(main.app, raise_server_exceptions=False)

    yield build
    main.app.dependency_overrides.clear()


def test_feedback_is_stored(make):
    store = FakeStore()
    payload = {"answer_id": ANSWER_ID, "rating": "down", "reason": "wrong_answer", "comment": "no"}
    response = make(store).post("/api/v1/feedback", json=payload)
    assert response.status_code == 200
    assert response.json() == {"saved": True}
    assert store.calls == [(ANSWER_ID, "down", "wrong_answer", "no")]


def test_feedback_for_an_unknown_answer_is_404(make):
    response = make(FakeStore(known=False)).post(
        "/api/v1/feedback", json={"answer_id": ANSWER_ID, "rating": "up"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "unknown_answer"


@pytest.mark.parametrize(
    "payload",
    [
        {"answer_id": "not-a-uuid", "rating": "up"},
        {"answer_id": ANSWER_ID, "rating": "meh"},
        {"answer_id": ANSWER_ID, "rating": "up", "reason": "boring"},
        {"answer_id": ANSWER_ID, "rating": "up", "comment": "x" * 1001},
    ],
)
def test_bad_feedback_is_rejected(make, payload):
    assert make(FakeStore()).post("/api/v1/feedback", json=payload).status_code == 422


def test_status_is_off_without_a_configured_key(make):
    response = make(FakeStore(), key="").get("/api/v1/status", headers={"X-Admin-Key": ""})
    assert response.status_code == 403


def test_status_needs_the_right_key(make):
    client = make(FakeStore(), key="secret-key")
    assert client.get("/api/v1/status").status_code == 401
    assert client.get("/api/v1/status", headers={"X-Admin-Key": "wrong"}).status_code == 401
    ok = client.get("/api/v1/status", headers={"X-Admin-Key": "secret-key"})
    assert ok.status_code == 200
    assert ok.json()["answers_saved"] == 0
