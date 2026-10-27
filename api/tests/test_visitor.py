"""Signed visitor tokens: forged, expired and missing tokens never get in."""

import time
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app import ask as ask_module
from app import main
from app import visitor as visitor_module
from app.config import Settings
from app.schemas import Answer, AskResponse
from app.visitor import issue_token, verify_token

SECRET = "unit-test-secret"
OTHER = "another-secret"


def test_a_token_round_trips():
    visitor = uuid4()
    token = issue_token(visitor, SECRET, 60)
    assert verify_token(token, SECRET) == visitor


@pytest.mark.parametrize(
    "mutate",
    [
        lambda t: t[:-1] + ("0" if t[-1] != "0" else "1"),  # signature changed
        lambda t: t.replace("v1.", "v2.", 1),  # wrong version
        lambda t: t.rsplit(".", 1)[0],  # signature missing
        lambda t: "x" * 300,  # too long
        lambda t: "",
        lambda t: "not-a-token",
    ],
)
def test_tampered_or_garbage_tokens_are_refused(mutate):
    token = issue_token(uuid4(), SECRET, 60)
    assert verify_token(mutate(token), SECRET) is None


def test_another_visitor_id_with_the_same_signature_is_refused():
    token = issue_token(uuid4(), SECRET, 60)
    _, _, expiry, signature = token.split(".")
    forged = f"v1.{uuid4()}.{expiry}.{signature}"
    assert verify_token(forged, SECRET) is None


def test_a_token_signed_with_another_secret_is_refused():
    assert verify_token(issue_token(uuid4(), OTHER, 60), SECRET) is None


def test_an_expired_token_is_refused():
    token = issue_token(uuid4(), SECRET, 60, now=time.time() - 3600)
    assert verify_token(token, SECRET) is None


def test_no_secret_means_nothing_is_trusted():
    token = issue_token(uuid4(), SECRET, 60)
    assert verify_token(token, "") is None


class FakeStore:
    def __init__(self):
        self.visitors: set[UUID] = set()
        self.saved = 0

    def create_visitor(self):
        visitor = uuid4()
        self.visitors.add(visitor)
        return visitor

    def visitor_exists(self, visitor_id):
        return visitor_id in self.visitors

    def save_answer(self, visitor_id, question, answer, index_version):
        self.saved += 1
        return str(uuid4())


class FakeService:
    def ask(self, question, compare):
        return AskResponse(answer_id="a", answer=Answer(mode="local", status="answered", text="ok"))


@pytest.fixture
def make(monkeypatch):
    def build(secret=SECRET):
        store = FakeStore()
        settings = Settings(visitor_token_secret=secret)
        monkeypatch.setattr(main, "get_settings", lambda: settings)
        monkeypatch.setattr(visitor_module, "get_settings", lambda: settings)
        main.app.dependency_overrides[main.get_store] = lambda: store
        main.app.dependency_overrides[ask_module.get_ask_service] = lambda: FakeService()
        return TestClient(main.app, raise_server_exceptions=False), store

    yield build
    main.app.dependency_overrides.clear()


def test_a_new_browser_gets_a_new_visitor(make):
    client, store = make()
    body = client.post("/api/v1/visitor", json={}).json()
    assert len(store.visitors) == 1
    assert verify_token(body["token"], SECRET) in store.visitors
    assert body["max_age_seconds"] > 0


def test_a_known_token_keeps_the_same_visitor(make):
    client, store = make()
    first = client.post("/api/v1/visitor", json={}).json()["token"]
    second = client.post("/api/v1/visitor", json={"token": first}).json()["token"]
    assert len(store.visitors) == 1
    assert verify_token(second, SECRET) == verify_token(first, SECRET)


def test_a_forged_token_gets_a_new_visitor_not_the_old_one(make):
    client, store = make()
    victim = client.post("/api/v1/visitor", json={}).json()["token"]
    forged = victim[:-1] + ("0" if victim[-1] != "0" else "1")
    new = client.post("/api/v1/visitor", json={"token": forged}).json()["token"]
    assert verify_token(new, SECRET) != verify_token(victim, SECRET)
    assert len(store.visitors) == 2


def test_a_token_of_a_deleted_visitor_gets_a_new_visitor(make):
    client, store = make()
    token = client.post("/api/v1/visitor", json={}).json()["token"]
    store.visitors.clear()
    new = client.post("/api/v1/visitor", json={"token": token}).json()["token"]
    assert verify_token(new, SECRET) in store.visitors


def test_without_a_secret_no_token_is_issued(make):
    client, _ = make(secret="")
    response = client.post("/api/v1/visitor", json={})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "visitor_not_configured"


def test_ask_needs_a_valid_token(make):
    client, store = make()
    body = {"question": "Hi"}
    assert client.post("/api/v1/ask", json=body).status_code == 401
    assert (
        client.post("/api/v1/ask", json=body, headers={"X-Visitor-Token": "forged"}).status_code
        == 401
    )
    token = client.post("/api/v1/visitor", json={}).json()["token"]
    ok = client.post("/api/v1/ask", json=body, headers={"X-Visitor-Token": token})
    assert ok.status_code == 200
    assert store.saved == 1


def test_feedback_needs_a_valid_token(make):
    client, _ = make()
    payload = {"answer_id": str(uuid4()), "rating": "up"}
    response = client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "visitor_required"
