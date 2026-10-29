"""A database that cannot be reached is a clear, retryable 503; other database errors stay a 500."""

import logging
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeout

from app import ask as ask_module
from app import main
from app import visitor as visitor_module
from app.config import Settings
from app.schemas import Answer, AskResponse
from app.visitor import issue_token

SECRET = "unit-test-secret"
LEAK = "password=hunter2 host=10.0.0.5"


class BrokenStore:
    """Every call fails the way the database driver would."""

    def __init__(self, error):
        self.error = error

    def visitor_exists(self, visitor_id):
        raise self.error

    def create_visitor(self):
        raise self.error

    def list_history(self, visitor_id, limit=50):
        raise self.error


class Service:
    def ask(self, question, compare):
        return AskResponse(answer_id="a", answer=Answer(mode="local", status="answered", text="ok"))


@pytest.fixture
def make(monkeypatch):
    def build(error):
        settings = Settings(visitor_token_secret=SECRET)
        for module in (main, visitor_module):
            monkeypatch.setattr(module, "get_settings", lambda: settings)
        main.app.dependency_overrides[main.get_store] = lambda: BrokenStore(error)
        main.app.dependency_overrides[ask_module.get_ask_service] = lambda: Service()
        return TestClient(main.app, raise_server_exceptions=False)

    yield build
    main.app.dependency_overrides.clear()


DOWN = [
    OperationalError("SELECT 1", {}, Exception(LEAK)),
    InterfaceError("SELECT 1", {}, Exception(LEAK)),
    PoolTimeout(LEAK),
]


@pytest.mark.parametrize("error", DOWN, ids=lambda e: type(e).__name__)
def test_a_database_that_is_down_gives_a_retryable_503_without_details(make, error, caplog):
    client = make(error)
    token = issue_token(uuid4(), SECRET, 60)
    caplog.set_level(logging.INFO)
    response = client.post(
        "/api/v1/ask", json={"question": "Hi"}, headers={"X-Visitor-Token": token}
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "storage_unavailable"
    assert response.headers["retry-after"] == "5"
    assert "hunter2" not in response.text
    ours = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("graphlens"))
    assert "hunter2" not in ours
    assert "request_id=" in ours


def test_creating_a_visitor_with_the_database_down_is_also_a_503(make):
    response = make(DOWN[0]).post("/api/v1/visitor", json={})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "storage_unavailable"


def test_a_broken_query_is_still_our_bug_and_stays_a_500(make):
    error = IntegrityError("INSERT", {}, Exception(LEAK))
    token = issue_token(uuid4(), SECRET, 60)
    response = make(error).get("/api/v1/history", headers={"X-Visitor-Token": token})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "hunter2" not in response.text
