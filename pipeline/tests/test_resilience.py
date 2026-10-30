"""Retry for reads and the model breaker (fake clock, fake sleeping, fake model)."""

import pytest
from neo4j.exceptions import ServiceUnavailable
from sqlalchemy.exc import OperationalError

from graphlens_pipeline.llm import LlmError, LlmResult
from graphlens_pipeline.resilience import (
    CircuitBreaker,
    GuardedLlm,
    retry_reads,
    transient_errors,
)


def flaky(failures, error=None):
    error = error or ConnectionError("dropped")
    calls = []

    def fn(x):
        calls.append(x)
        if len(calls) <= failures:
            raise error
        return x * 2

    return fn, calls


def test_a_read_that_fails_twice_and_then_works_returns_its_result_after_backing_off():
    waits = []
    fn, calls = flaky(2)
    assert retry_reads(fn, sleep=waits.append)(21) == 42
    assert len(calls) == 3 and waits == [pytest.approx(0.2), pytest.approx(0.6)]


def test_it_gives_up_after_the_last_attempt_with_the_real_error():
    waits = []
    fn, calls = flaky(5, ConnectionError("still down"))
    with pytest.raises(ConnectionError, match="still down"):
        retry_reads(fn, attempts=3, sleep=waits.append)(1)
    assert len(calls) == 3 and len(waits) == 2


def test_a_real_bug_is_not_retried():
    fn, calls = flaky(5, ValueError("bad query"))
    with pytest.raises(ValueError):
        retry_reads(fn, sleep=lambda s: None)(1)
    assert len(calls) == 1


def test_the_transient_list_covers_the_databases_we_use():
    errors = transient_errors()
    assert issubclass(ServiceUnavailable, errors)
    assert issubclass(OperationalError, errors)
    assert issubclass(ConnectionError, errors) and issubclass(TimeoutError, errors)
    assert not issubclass(ValueError, errors)


class Clock:
    now = 100.0

    def __call__(self):
        return self.now


def test_the_breaker_opens_pauses_lets_one_trial_through_and_closes_on_success():
    clock = Clock()
    breaker = CircuitBreaker(failures=2, pause_seconds=30, clock=clock)
    breaker.record_failure()
    assert breaker.allow()
    breaker.record_failure()
    assert breaker.is_open and not breaker.allow()
    clock.now += 31
    assert breaker.allow() and not breaker.allow()  # one trial only
    breaker.record_success()
    assert not breaker.is_open and breaker.allow()


def test_a_failed_trial_restarts_the_pause():
    clock = Clock()
    breaker = CircuitBreaker(failures=1, pause_seconds=30, clock=clock)
    breaker.record_failure()
    clock.now += 31
    breaker.allow()
    breaker.record_failure()
    clock.now += 29
    assert not breaker.allow()


class FakeModel:
    model = "gpt-4.1-mini"

    def __init__(self, fail=0):
        self.fail, self.calls = fail, 0

    def complete(self, system, user, max_output_tokens, json_schema=None):
        self.calls += 1
        if self.calls <= self.fail:
            raise LlmError("model call failed (APIConnectionError)")
        return LlmResult("ok", self.model, 10, 5, "stop")


def test_the_model_is_not_retried_by_the_guard():
    model = FakeModel(fail=1)
    guarded = GuardedLlm(model)
    with pytest.raises(LlmError):
        guarded.complete("s", "u", 10)
    assert model.calls == 1


def test_after_repeated_model_failures_calls_fail_at_once_without_reaching_the_model():
    model = FakeModel(fail=99)
    guarded = GuardedLlm(model, CircuitBreaker(failures=3, pause_seconds=60))
    for _ in range(3):
        with pytest.raises(LlmError):
            guarded.complete("s", "u", 10)
    with pytest.raises(LlmError, match="paused"):
        guarded.complete("s", "u", 10)
    assert model.calls == 3


def test_a_working_model_passes_through_and_keeps_its_name():
    guarded = GuardedLlm(FakeModel())
    assert guarded.model == "gpt-4.1-mini"
    assert guarded.complete("s", "u", 10).text == "ok"


def test_plain_rag_retrieval_is_retried_through_the_search_argument(monkeypatch):
    from graphlens_pipeline import answer as answer_module
    from graphlens_pipeline.answer import Passage, answer_question

    calls = []

    def search(client, engine, embedder, question, k, collection):
        calls.append(question)
        if len(calls) == 1:
            raise ConnectionError("qdrant dropped")
        return [Passage(0, "u_1", "Evidence.", "1 Intro", "Paper", "2023.1", 0.5)]

    class Llm:
        model = "m"

        def complete(self, system, user, max_output_tokens, **kwargs):
            return LlmResult("Fact [1].", "m", 100, 10)

    monkeypatch.setattr(answer_module.time, "sleep", lambda s: None)
    result = answer_question(
        "What is X?", None, None, None, Llm(), search=retry_reads(search, sleep=lambda s: None)
    )
    assert len(calls) == 2 and not result.refused


def test_relate_graph_reads_are_retried_through_the_find_and_shared_arguments():
    from graphlens_pipeline.relate import answer_relate

    seen = []

    def find(driver, a, b, predicates, version):
        seen.append("find")
        if seen.count("find") == 1:
            raise ServiceUnavailable("neo4j dropped")
        return []

    def shared(driver, a, b, version):
        seen.append("shared")
        if seen.count("shared") == 1:
            raise ServiceUnavailable("neo4j dropped")
        return [{"title": "Topic"}]

    class Index:
        pass

    import graphlens_pipeline.relate as relate_module

    ends = (type("E", (), {"id": "a", "name": "A"})(), type("E", (), {"id": "b", "name": "B"})())
    original = relate_module.link_pair
    relate_module.link_pair = lambda index, question: (ends, None)
    try:
        answer = answer_relate(
            None, None, Index(), "How is A related to B?", [], "v", lambda ids: {}, len,
            find=retry_reads(find, sleep=lambda s: None),
            shared=retry_reads(shared, sleep=lambda s: None),
        )  # fmt: skip
    finally:
        relate_module.link_pair = original
    assert answer.status == "no_path" and seen == ["find", "find", "shared", "shared"]
    assert answer.shared_communities == [{"title": "Topic"}]
