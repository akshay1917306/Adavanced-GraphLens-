"""The circuit breaker, with a fake clock."""

from app.breaker import CircuitBreaker


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(failures=3, pause=30.0):
    clock = Clock()
    return CircuitBreaker(failures, pause, clock), clock


def test_it_stays_closed_below_the_failure_limit():
    breaker, _ = make()
    for _ in range(2):
        breaker.record_failure()
    assert breaker.allow() and not breaker.is_open


def test_a_success_resets_the_count():
    breaker, _ = make()
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.allow()


def test_it_opens_at_the_limit_and_refuses_calls_during_the_pause():
    breaker, clock = make()
    for _ in range(3):
        breaker.record_failure()
    assert breaker.is_open and not breaker.allow()
    clock.now += 29
    assert not breaker.allow()


def test_after_the_pause_exactly_one_trial_call_is_let_through():
    breaker, clock = make()
    for _ in range(3):
        breaker.record_failure()
    clock.now += 31
    assert breaker.allow() is True  # the trial
    assert breaker.allow() is False  # nobody else while the trial runs


def test_a_successful_trial_closes_it():
    breaker, clock = make()
    for _ in range(3):
        breaker.record_failure()
    clock.now += 31
    breaker.allow()
    breaker.record_success()
    assert not breaker.is_open and breaker.allow() and breaker.allow()


def test_a_failed_trial_opens_it_again_for_a_full_pause():
    breaker, clock = make()
    for _ in range(3):
        breaker.record_failure()
    clock.now += 31
    breaker.allow()
    breaker.record_failure()
    assert not breaker.allow()
    clock.now += 29
    assert not breaker.allow()
    clock.now += 2
    assert breaker.allow()
