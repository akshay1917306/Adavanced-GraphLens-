"""Streaming of the answer text: the model client, the hook, and the service's /search/stream."""

import json
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from graphlens_pipeline.llm import (
    LlmError,
    LlmResult,
    OpenAiLlm,
    delta_kwargs,
    reset_delta_sink,
    set_delta_sink,
)
from graphlens_pipeline.resilience import CircuitBreaker, GuardedLlm
from graphlens_pipeline.searchservice import Backends, SearchService, create_app

KEY = "k" * 20


# ------------------------------------------------------------------ the model client


def chunk(text=None, finish=None, usage=None, model="gpt-4.1-mini-2025"):
    choices = [SimpleNamespace(delta=SimpleNamespace(content=text), finish_reason=finish)]
    return SimpleNamespace(model=model, choices=choices if usage is None else [], usage=usage)


class FakeCompletions:
    def __init__(self, chunks, error=None):
        self.chunks, self.error, self.options = chunks, error, None

    def create(self, **options):
        self.options = options
        if self.error:
            raise self.error
        return iter(self.chunks)


def streaming_llm(monkeypatch, completions):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real-0000000000")
    llm = OpenAiLlm(model="gpt-4.1-mini")
    llm._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return llm


def test_streaming_gives_each_piece_and_the_same_result_as_one_call(monkeypatch):
    usage = SimpleNamespace(prompt_tokens=120, completion_tokens=7)
    completions = FakeCompletions(
        [chunk("Hel"), chunk("lo [T1]"), chunk(None, finish="stop"), chunk(usage=usage)]
    )
    seen = []
    result = streaming_llm(monkeypatch, completions).complete("s", "u", 50, on_delta=seen.append)
    assert seen == ["Hel", "lo [T1]"]
    assert result == LlmResult("Hello [T1]", "gpt-4.1-mini-2025", 120, 7, "stop")
    assert completions.options["stream"] is True
    assert completions.options["stream_options"] == {"include_usage": True}


def test_a_stream_that_breaks_is_an_llm_error_without_details(monkeypatch):
    completions = FakeCompletions([], error=ConnectionError("secret-detail"))
    with pytest.raises(LlmError) as raised:
        streaming_llm(monkeypatch, completions).complete("s", "u", 50, on_delta=lambda t: None)
    assert "secret-detail" not in str(raised.value) and "ConnectionError" in str(raised.value)


def test_a_json_schema_call_is_never_streamed(monkeypatch):
    class OneShot:
        options = None

        def create(self, **options):
            self.options = options
            message = SimpleNamespace(content="{}")
            choice = SimpleNamespace(message=message, finish_reason="stop")
            usage = SimpleNamespace(prompt_tokens=1, completion_tokens=1)
            return SimpleNamespace(choices=[choice], usage=usage, model="m")

    completions = OneShot()
    seen = []
    streaming_llm(monkeypatch, completions).complete(
        "s", "u", 50, json_schema={"type": "object"}, on_delta=seen.append
    )
    assert "stream" not in completions.options and seen == []


# ------------------------------------------------------------------ the hook


def test_the_hook_is_empty_unless_a_sink_is_set():
    assert delta_kwargs() == {}
    token = set_delta_sink(print)
    try:
        assert delta_kwargs() == {"on_delta": print}
    finally:
        reset_delta_sink(token)
    assert delta_kwargs() == {}


class PlainFake:
    model = "m"

    def __init__(self):
        self.calls = []

    def complete(self, system, user, max_output_tokens, json_schema=None, **extra):
        self.calls.append(extra)
        return LlmResult("x", "m", 1, 1, "stop")


def test_the_guarded_client_forwards_the_sink_only_when_there_is_one():
    inner = PlainFake()
    guarded = GuardedLlm(inner, CircuitBreaker())
    guarded.complete("s", "u", 10)
    guarded.complete("s", "u", 10, on_delta=print)
    assert inner.calls == [{}, {"on_delta": print}]


# ------------------------------------------------------------------ the service


def reply(mode="local"):
    return {
        "mode": mode, "status": "answered", "text": "Hello", "message": None,
        "citations": [], "nodes": [], "links": [], "check_status": "verified",
        "model": "", "cost_usd": 0.003, "latency_ms": 0,
    }  # fmt: skip


def backends(seen_sinks):
    """A local mode that writes its answer in two pieces through the hook, like the real one."""

    def local(question):
        sink = delta_kwargs().get("on_delta")
        seen_sinks.append(sink)
        if sink:
            sink("Hel")
            sink("lo")
        return reply("local")

    def baseline(question):
        seen_sinks.append(delta_kwargs().get("on_delta"))
        return reply("baseline")

    route = SimpleNamespace(
        mode="local", source="rules", confidence=0.9, ran_as_fallback=False, cost_usd=0.0
    )
    return Backends(lambda q: route, local, local, local, baseline)


def test_the_main_answer_streams_and_the_comparison_answer_does_not():
    sinks = []
    out = SearchService(backends(sinks)).ask("q", compare=True, on_delta=lambda t: None)
    assert sinks[0] is not None and sinks[1] is None  # local streamed, baseline not
    assert out["answer"]["mode"] == "local" and out["baseline"]["mode"] == "baseline"
    assert delta_kwargs() == {}  # the sink does not leak out of the call


def stream(c, body=None, key=KEY):
    headers = {"X-Search-Key": key} if key else {}
    return c.post("/search/stream", json=body or {"question": "q"}, headers=headers)


def events(response):
    return [json.loads(line) for line in response.text.splitlines() if line]


def test_the_stream_sends_pieces_then_the_final_reply():
    app = create_app(lambda: SearchService(backends([])), KEY)
    with TestClient(app) as c:
        response = stream(c)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    out = events(response)
    assert [e["type"] for e in out] == ["delta", "delta", "final"]
    assert "".join(e["text"] for e in out[:2]) == "Hello"
    assert out[2]["reply"]["answer"]["text"] == "Hello" and out[2]["reply"]["baseline"] is None


def test_the_stream_needs_the_shared_key_and_a_valid_body():
    app = create_app(lambda: SearchService(backends([])), KEY)
    with TestClient(app) as c:
        assert stream(c, key=None).status_code == 401
        assert stream(c, key="x" * 20).status_code == 401
        assert stream(c, {"question": ""}).status_code == 422


class Failing:
    def ask(self, question, compare, on_delta=None):
        on_delta("partial")
        raise RuntimeError("the question was: secret question text")


def test_a_failure_in_the_middle_is_an_error_event_without_the_question(caplog):
    caplog.set_level("INFO")
    app = create_app(lambda: Failing(), KEY)
    with TestClient(app) as c:
        out = events(stream(c))
    assert [e["type"] for e in out] == ["delta", "error"] and out[1]["code"] == "search_failed"
    assert "secret question text" not in caplog.text


class Stuck:
    def __init__(self):
        self.release = threading.Event()

    def ask(self, question, compare, on_delta=None):
        self.release.wait(5)
        return {"answer": reply(), "baseline": None, "route": {}}


def test_a_stream_that_runs_too_long_ends_with_a_timeout_event_and_keeps_its_slot():
    stuck = Stuck()
    app = create_app(lambda: stuck, KEY, max_concurrent=1, queue_wait=0.1, deadline=0.2)
    with TestClient(app) as c:
        out = events(stream(c))
        assert out == [{"type": "error", "code": "search_timeout"}]
        busy = stream(c)
        assert busy.status_code == 503 and busy.json()["error"]["code"] == "busy"
        stuck.release.set()
