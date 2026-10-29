"""Streaming answers: the live client reads lines, the route sends them on."""

import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app import ask as ask_module
from app import main
from app import visitor as visitor_module
from app.breaker import CircuitBreaker
from app.live import EngineTimeout, LiveService

KEY = "shared-test-key-1234"
LEAK = "password=hunter2 host=10.0.0.5"


def answer(**fields):
    base = {
        "mode": "local", "status": "answered", "text": "KGT5 is small [T1].", "message": None,
        "citations": [], "nodes": [], "links": [], "check_status": "verified",
        "model": "gpt-4.1-mini", "cost_usd": 0.0035, "latency_ms": 900,
    }  # fmt: skip
    base.update(fields)
    return base


def lines(*events):
    return "".join(json.dumps(e) + "\n" for e in events).encode()


FINAL = {"type": "final", "reply": {"answer": answer(), "baseline": None, "route": {}}}
DELTAS = [{"type": "delta", "text": "KGT5 is "}, {"type": "delta", "text": "small [T1]."}]


def service(handler, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://search:8100")
    return LiveService("http://search:8100", KEY, client=client, **kwargs)


def streaming(*events):
    def handler(request):
        assert request.url.path == "/search/stream" and request.headers["x-search-key"] == KEY
        return httpx.Response(200, content=lines(*events))

    return handler


# ---------------------------------------------------------------- the live client


def test_pieces_come_first_then_the_final_answer():
    out = list(service(streaming(*DELTAS, FINAL)).open_stream("Hi?", False))
    assert [k for k, _ in out] == ["delta", "delta", "final"]
    assert "".join(v for k, v in out if k == "delta") == "KGT5 is small [T1]."
    final = out[-1][1]
    assert final.answer.text.startswith("KGT5") and final.fixture is False


def test_a_refusal_after_a_streamed_draft_replaces_it():
    refused = answer(status="refused", text="", message="No evidence.")
    final = {"type": "final", "reply": {"answer": refused, "baseline": None}}
    out = list(service(streaming(*DELTAS, final)).open_stream("Q", False))
    assert out[-1][1].answer.status == "refused" and out[-1][1].answer.text == ""


@pytest.mark.parametrize("status", [401, 422, 500, 503])
def test_a_refusal_before_the_first_byte_is_unavailable_and_counts_as_a_failure(status):
    breaker = CircuitBreaker(failures=1)
    live = service(lambda r: httpx.Response(status, json={"error": LEAK}), breaker=breaker)
    from app.ask import EngineUnavailable

    with pytest.raises(EngineUnavailable) as caught:
        live.open_stream("Hi?", False)
    assert "hunter2" not in str(caught.value) and breaker.is_open


def test_a_504_before_the_first_byte_is_a_timeout():
    with pytest.raises(EngineTimeout):
        service(lambda r: httpx.Response(504, json={})).open_stream("Hi?", False)


def test_an_error_event_in_the_middle_raises_and_counts_as_a_failure():
    breaker = CircuitBreaker(failures=1)
    live = service(
        streaming(DELTAS[0], {"type": "error", "code": "search_timeout"}), breaker=breaker
    )
    stream = live.open_stream("Hi?", False)
    assert next(stream) == ("delta", "KGT5 is ")
    with pytest.raises(EngineTimeout):
        next(stream)
    assert breaker.is_open


def test_a_stream_that_ends_without_a_final_answer_is_unavailable():
    from app.ask import EngineUnavailable

    with pytest.raises(EngineUnavailable):
        list(service(streaming(*DELTAS)).open_stream("Hi?", False))


def test_a_final_reply_with_an_unknown_field_is_refused_without_leaking_it():
    from app.ask import EngineUnavailable

    bad = {"type": "final", "reply": {"answer": answer(secret_field=LEAK), "baseline": None}}
    with pytest.raises(EngineUnavailable) as caught:
        list(service(streaming(bad)).open_stream("Hi?", False))
    assert "hunter2" not in str(caught.value)


def test_garbage_is_unavailable():
    from app.ask import EngineUnavailable

    handler = lambda r: httpx.Response(200, content=b"not json\n")  # noqa: E731
    with pytest.raises(EngineUnavailable):
        list(service(handler).open_stream("Hi?", False))


def test_the_total_time_is_limited_even_when_pieces_keep_coming(monkeypatch):
    clock = iter([0.0, 0.0, 100.0, 100.0, 100.0])
    monkeypatch.setattr("app.live.time.monotonic", lambda: next(clock))
    with pytest.raises(EngineTimeout):
        list(service(streaming(*DELTAS, FINAL)).open_stream("Hi?", False, timeout_seconds=45))


# ---------------------------------------------------------------- the route


class FakeStore:
    def __init__(self, fail=False):
        self.saved, self.fail = [], fail

    def save_answer(self, visitor_id, question, answer, index_version):
        if self.fail:
            raise RuntimeError(LEAK)
        self.saved.append(question)
        return "11111111-1111-1111-1111-111111111111"


class FakeLimiter:
    def __init__(self):
        self.costs = []

    def hit(self, *args):
        return None

    def ensure_room(self, cap):
        return None

    def record_cost(self, usd):
        self.costs.append(usd)


@pytest.fixture
def client():
    def make(svc, store=None, limiter=None):
        from app import ratelimit

        main.app.dependency_overrides[ask_module.get_ask_service] = lambda: svc
        main.app.dependency_overrides[main.get_store] = lambda: store or FakeStore()
        main.app.dependency_overrides[ratelimit.get_limiter] = lambda: limiter or FakeLimiter()
        main.app.dependency_overrides[visitor_module.get_visitor] = lambda: uuid4()
        return TestClient(main.app, raise_server_exceptions=False)

    yield make
    main.app.dependency_overrides.clear()


def events(response):
    return [json.loads(line) for line in response.text.splitlines() if line]


def post(c, **body):
    return c.post("/api/v1/ask/stream", json={"question": "Hi?", **body})


def test_the_route_sends_pieces_then_the_saved_final_answer_and_counts_the_cost(client):
    store, limiter = FakeStore(), FakeLimiter()
    response = post(client(service(streaming(*DELTAS, FINAL)), store, limiter))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    out = events(response)
    assert [e["type"] for e in out] == ["delta", "delta", "final"]
    final = out[-1]["response"]
    assert final["saved"] is True and final["answer_id"].startswith("11111111")
    assert final["answer"]["text"].startswith("KGT5")
    assert store.saved == ["Hi?"] and limiter.costs == [0.0035]


def test_a_failed_save_still_gives_the_answer_and_never_leaks_why(client):
    out = events(post(client(service(streaming(*DELTAS, FINAL)), FakeStore(fail=True))))
    assert out[-1]["response"]["saved"] is False and "hunter2" not in json.dumps(out)


def test_an_error_in_the_middle_is_an_error_line_and_nothing_is_charged_or_saved(client):
    store, limiter = FakeStore(), FakeLimiter()
    handler = streaming(DELTAS[0], {"type": "error", "code": "search_failed"})
    out = events(post(client(service(handler), store, limiter)))
    assert [e["type"] for e in out] == ["delta", "error"]
    assert out[-1]["code"] == "engine_unavailable"
    assert store.saved == [] and limiter.costs == []


def test_a_problem_before_the_first_byte_is_a_normal_http_error(client):
    unavailable = service(lambda r: httpx.Response(500, json={"error": LEAK}))
    response = post(client(unavailable))
    assert response.status_code == 503 and "hunter2" not in response.text
    assert response.json()["error"]["code"] == "engine_unavailable"
    slow = service(lambda r: httpx.Response(504, json={}))
    assert post(client(slow)).status_code == 504


def test_a_service_without_streaming_answers_with_one_final_line(client):
    class Replay:
        def ask(self, question, compare):
            from app.schemas import Answer, AskResponse

            return AskResponse(
                answer_id="r1",
                answer=Answer(mode="local", status="answered", text="saved"),
                fixture=True,
            )

    out = events(post(client(Replay())))
    assert [e["type"] for e in out] == ["final"] and out[0]["response"]["fixture"] is True


def test_the_input_rules_are_the_same_as_for_ask(client):
    c = client(service(streaming(FINAL)))
    assert c.post("/api/v1/ask/stream", json={"question": ""}).status_code == 422
    assert c.post("/api/v1/ask/stream", json={"question": "x", "extra": 1}).status_code == 422
