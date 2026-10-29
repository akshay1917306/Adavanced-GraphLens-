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
