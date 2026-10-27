"""Security headers, request ids, the body limit, log hygiene and the admin audit trail."""

import json
import logging
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import ask as ask_module
from app import main
from app import ratelimit as rl
from app import visitor as visitor_module
from app.config import Settings
from app.schemas import Answer, AskResponse
from tests.test_ratelimit import FakeRedis

MARKER = "SECRET-MARKER-9f3a"


class FakeStore:
    def __init__(self):
        self.audit_rows: list[str] = []

    def visitor_exists(self, visitor_id):
        return True

    def save_answer(self, visitor_id, question, answer, index_version):
        return str(uuid4())

    def audit(self, action, target=None):
        self.audit_rows.append(action)

    def status(self):
        return {"runs": [], "quality_checks": [], "answers_saved": 0, "feedback_saved": 0}


class Service:
    def ask(self, question, compare):
        return AskResponse(answer_id="a", answer=Answer(mode="local", status="answered", text="ok"))

    def examples(self):
        return ["one"]


@pytest.fixture
def make(monkeypatch):
    def build(admin_key="", admin_per_min=10):
        store = FakeStore()
        settings = Settings(
            visitor_token_secret="s", admin_api_key=admin_key, rate_admin_ip_per_min=admin_per_min
        )
        for module in (main, visitor_module, rl):
            monkeypatch.setattr(module, "get_settings", lambda: settings)
        main.app.dependency_overrides[main.get_store] = lambda: store
        limiter = rl.Limiter(FakeRedis())  # one limiter for the whole test, so counts add up
        main.app.dependency_overrides[rl.get_limiter] = lambda: limiter
        main.app.dependency_overrides[ask_module.get_ask_service] = lambda: Service()
        main.app.dependency_overrides[visitor_module.get_visitor] = lambda: uuid4()
        return TestClient(main.app, raise_server_exceptions=False), store

    yield build
    main.app.dependency_overrides.clear()


def test_every_response_carries_the_security_headers_and_a_request_id(make):
    client, _ = make()
    response = client.get("/api/v1/examples")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert len(response.headers["x-request-id"]) >= 8


def test_errors_get_the_headers_too(make):
    client, _ = make()
    response = client.post("/api/v1/ask", json={})
    assert response.status_code == 422
    assert response.headers["x-content-type-options"] == "nosniff"


def test_a_sane_request_id_is_kept_and_a_strange_one_is_replaced(make):
    client, _ = make()
    assert (
        client.get("/api/v1/examples", headers={"X-Request-Id": "abc-12345678"}).headers[
            "x-request-id"
        ]
        == "abc-12345678"
    )
    bad = client.get("/api/v1/examples", headers={"X-Request-Id": "<script>alert(1)</script>"})
    assert "<" not in bad.headers["x-request-id"]


def test_the_api_docs_page_keeps_working_without_the_strict_policy(make):
    client, _ = make()
    docs = client.get("/openapi.json")
    assert docs.status_code == 200
    assert "content-security-policy" not in docs.headers


def test_a_body_without_content_length_is_refused(make):
    client, _ = make()
    response = client.post(
        "/api/v1/ask",
        content=iter([b'{"question": "x"}']),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 411


def test_an_oversized_body_is_refused_before_it_is_read(make):
    client, _ = make()
    big = json.dumps({"question": "x" * 40_000})
    response = client.post("/api/v1/ask", content=big, headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "too_large"


def test_logs_have_the_request_but_never_what_the_person_typed(make, caplog):
    client, _ = make()
    caplog.set_level(logging.INFO)
    client.post(
        "/api/v1/ask?trace=" + MARKER,
        json={"question": MARKER + " question text"},
        headers={"X-Visitor-Token": MARKER},
    )
    ours = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("graphlens"))
    assert MARKER not in ours
    lines = [json.loads(r.getMessage()) for r in caplog.records if r.name == "graphlens.request"]
    assert lines[-1]["route"] == "/api/v1/ask"
    assert lines[-1]["status"] == 200
    assert lines[-1]["method"] == "POST"
    assert set(lines[-1]) == {"request_id", "method", "route", "status", "ms"}


def test_an_unexpected_error_is_logged_by_type_and_request_id_only(make, caplog):
    client, _ = make()

    class Boom:
        def ask(self, question, compare):
            raise RuntimeError(f"db password {MARKER}")

    main.app.dependency_overrides[ask_module.get_ask_service] = lambda: Boom()
    caplog.set_level(logging.INFO)
    response = client.post("/api/v1/ask", json={"question": "hello"})
    assert response.status_code == 500
    ours = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("graphlens"))
    assert MARKER not in ours
    assert "RuntimeError" in ours


def test_admin_views_and_refusals_are_written_to_the_audit_log(make):
    client, store = make(admin_key="the-key")
    assert client.get("/api/v1/status", headers={"X-Admin-Key": "wrong"}).status_code == 401
    assert client.get("/api/v1/status").status_code == 401
    assert client.get("/api/v1/status", headers={"X-Admin-Key": "the-key"}).status_code == 200
    assert store.audit_rows == ["status_denied", "status_denied", "status_view"]


def test_guessing_the_admin_key_is_slowed_down(make):
    client, store = make(admin_key="the-key", admin_per_min=3)
    codes = [
        client.get("/api/v1/status", headers={"X-Admin-Key": f"guess{i}"}).status_code
        for i in range(5)
    ]
    assert codes == [401, 401, 401, 429, 429]
    assert len(store.audit_rows) == 3  # refused before the key is even looked at


def test_without_a_configured_key_the_status_page_is_off_and_not_audited(make):
    client, store = make(admin_key="")
    assert client.get("/api/v1/status", headers={"X-Admin-Key": "anything"}).status_code == 403
    assert store.audit_rows == []
