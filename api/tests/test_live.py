"""The live client: contract, time limit, retry rule, breaker, and the API around it."""

import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app import ask as ask_module
from app import main
from app import visitor as visitor_module
from app.ask import EngineUnavailable
from app.breaker import CircuitBreaker
from app.hardening import request_id_var
from app.live import EngineTimeout, LiveService

KEY = "shared-test-key-1234"
LEAK = "password=hunter2 host=10.0.0.5"


def answer(mode="local", **fields):
    base = {
        "mode": mode, "status": "answered", "text": "KGT5 is small [T1].", "message": None,
        "citations": [{"label": "T1", "kind": "text_unit", "title": "P", "text": "passage",
                       "source": None, "ref_id": "u_1"}],
        "nodes": [], "links": [], "check_status": "verified", "model": "gpt-4.1-mini",
        "cost_usd": 0.0035, "latency_ms": 900,
    }  # fmt: skip
    base.update(fields)
    return base


def service(handler, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://search:8100")
    return LiveService("http://search:8100", KEY, client=client, **kwargs)


def ok_handler(calls=None):
    def handler(request):
        if calls is not None:
            calls.append(request)
        body = {"answer": answer(), "baseline": None, "route": {"mode": "local"}}
        return httpx.Response(200, json=body)

    return handler


def test_a_good_reply_becomes_an_ask_response_and_the_key_and_request_id_are_sent():
    calls = []
    request_id_var.set("req-12345678")
    out = service(ok_handler(calls)).ask("Hi?", compare=False)
    assert out.answer.text.startswith("KGT5") and out.answer.cost_usd == 0.0035
    assert out.fixture is False and out.baseline is None and len(out.answer_id) >= 16
    sent = calls[0]
    assert sent.headers["x-search-key"] == KEY and sent.headers["x-request-id"] == "req-12345678"
    assert json.loads(sent.content) == {"question": "Hi?", "compare": False}


def test_compare_brings_back_a_second_answer():
    def handler(request):
        body = {"answer": answer(), "baseline": answer("baseline"), "route": None}
        return httpx.Response(200, json=body)

    out = service(handler).ask("Hi?", compare=True)
    assert out.baseline.mode == "baseline"


def test_a_reply_with_a_field_the_api_does_not_know_is_refused_without_leaking_it():
    def handler(request):
        return httpx.Response(200, json={"answer": answer(secret_field=LEAK), "baseline": None})

    with pytest.raises(EngineUnavailable) as caught:
        service(handler).ask("Hi?", False)
    assert "hunter2" not in str(caught.value)


@pytest.mark.parametrize("status", [401, 422, 500, 502, 503])
def test_any_non_200_answer_is_unavailable_and_counts_as_a_failure(status):
    breaker = CircuitBreaker(failures=1)
    live = service(lambda request: httpx.Response(status, json={"error": LEAK}), breaker=breaker)
    with pytest.raises(EngineUnavailable) as caught:
        live.ask("Hi?", False)
    assert "hunter2" not in str(caught.value) and breaker.is_open


def test_a_timeout_is_not_retried_because_the_request_may_already_be_paid_for():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(EngineTimeout):
        service(handler).ask("Hi?", False)
    assert len(calls) == 1


def test_a_connection_that_could_not_be_opened_is_retried_once(monkeypatch):
    monkeypatch.setattr("app.live.time.sleep", lambda s: None)
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(200, json={"answer": answer(), "baseline": None})

    assert service(handler).ask("Hi?", False).answer.status == "answered"
    assert len(calls) == 2


def test_two_connection_failures_in_a_row_are_unavailable(monkeypatch):
    monkeypatch.setattr("app.live.time.sleep", lambda s: None)
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(EngineUnavailable):
        service(handler).ask("Hi?", False)
    assert len(calls) == 2


def test_after_repeated_failures_calls_fail_at_once_without_touching_the_service():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(500, json={})

    live = service(handler, breaker=CircuitBreaker(failures=2, pause_seconds=60))
    for _ in range(2):
        with pytest.raises(EngineUnavailable):
            live.ask("Hi?", False)
    with pytest.raises(EngineUnavailable):
        live.ask("Hi?", False)
    assert len(calls) == 2  # the third call never left


def test_a_success_closes_the_breaker():
    breaker = CircuitBreaker(failures=2)
    live = service(ok_handler(), breaker=breaker)
    breaker.record_failure()
    live.ask("Hi?", False)
    breaker.record_failure()
    assert not breaker.is_open  # the earlier failure no longer counts


@pytest.mark.parametrize(("url", "key"), [("", KEY), ("http://search:8100", "")])
def test_live_mode_without_its_settings_refuses_to_start(url, key):
    with pytest.raises(RuntimeError):
        LiveService(url, key)


def test_the_example_list_is_available_and_the_service_says_it_is_live():
    live = service(ok_handler())
    assert len(live.examples()) >= 5 and live.live is True


# ---------------------------------------------------------------- the public API around it


class FakeStore:
    def visitor_exists(self, visitor_id):
        return True

    def save_answer(self, visitor_id, question, answer, index_version):
        return str(uuid4())


@pytest.fixture
def client():
    def make(live):
        main.app.dependency_overrides[ask_module.get_ask_service] = lambda: live
        main.app.dependency_overrides[main.get_store] = lambda: FakeStore()
        main.app.dependency_overrides[visitor_module.get_visitor] = lambda: uuid4()
        return TestClient(main.app, raise_server_exceptions=False)

    yield make
    main.app.dependency_overrides.clear()


def test_a_timeout_reaches_the_person_as_a_plain_504(client):
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    response = client(service(handler)).post("/api/v1/ask", json={"question": "Hi?"})
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "engine_timeout"


def test_an_unavailable_service_is_a_503_without_details(client):
    live = service(lambda request: httpx.Response(500, json={"error": LEAK}))
    response = client(live).post("/api/v1/ask", json={"question": "Hi?"})
    assert response.status_code == 503 and "hunter2" not in response.text
    assert response.json()["error"]["code"] == "engine_unavailable"


def test_the_cost_of_a_live_answer_is_in_the_response_and_the_examples_say_live(client):
    c = client(service(ok_handler()))
    body = c.post("/api/v1/ask", json={"question": "Hi?"}).json()
    assert body["answer"]["cost_usd"] == 0.0035 and body["fixture"] is False
    listing = c.get("/api/v1/examples").json()
    assert listing["live"] is True and len(listing["questions"]) >= 5
