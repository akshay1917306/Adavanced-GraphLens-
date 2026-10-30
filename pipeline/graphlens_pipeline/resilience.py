"""Retry for reads and a circuit breaker for the model, used by the internal search service.

Two rules decide what may be repeated:

- A **read** from Neo4j, Qdrant or Postgres is free and changes nothing, so a short, bounded retry
  with back-off after a transient failure is safe.
- A **model call** costs money, so it is never repeated here (the client already retries a failed
  connection). After several failures in a row the breaker stops sending calls for a while so every
  question does not wait for a timeout.

(`CircuitBreaker` is a small copy of the one in the API: the two live in separate images.)
"""

import functools
import threading
import time
from collections.abc import Callable

from graphlens_pipeline.llm import LlmError, LlmResult


def transient_errors() -> tuple[type[BaseException], ...]:
    """The exception types that mean "try again": a dropped connection, not a bad query."""
    errors: list[type[BaseException]] = [ConnectionError, TimeoutError]
    try:
        from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError

        errors += [ServiceUnavailable, SessionExpired, TransientError]
    except ImportError:  # pragma: no cover
        pass
    try:
        from qdrant_client.http.exceptions import ResponseHandlingException

        errors.append(ResponseHandlingException)
    except ImportError:  # pragma: no cover
        pass
    try:
        from sqlalchemy.exc import InterfaceError, OperationalError
        from sqlalchemy.exc import TimeoutError as PoolTimeout

        errors += [InterfaceError, OperationalError, PoolTimeout]
    except ImportError:  # pragma: no cover
        pass
    return tuple(errors)


def retry_reads(
    fn: Callable,
    attempts: int = 3,
    base_delay: float = 0.2,
    sleep: Callable[[float], None] = time.sleep,
    errors: tuple[type[BaseException], ...] | None = None,
) -> Callable:
    """`fn` again after a transient failure, waiting 0.2 s, then 0.6 s, and then it gives up."""
    catch = errors if errors is not None else transient_errors()

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        for attempt in range(attempts):
            try:
                return fn(*args, **kwargs)
            except catch:
                if attempt == attempts - 1:
                    raise
                sleep(base_delay * 3**attempt)

    return wrapper


class CircuitBreaker:
    def __init__(
        self,
        failures: int = 5,
        pause_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit, self._pause, self._clock = failures, pause_seconds, clock
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at: float | None = None
        self._trial_running = False

    def allow(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if self._clock() - self._opened_at < self._pause or self._trial_running:
                return False
            self._trial_running = True
            return True

    def record_success(self) -> None:
        with self._lock:
            self._failures, self._opened_at, self._trial_running = 0, None, False

    def record_failure(self) -> None:
        with self._lock:
            self._trial_running = False
            self._failures += 1
            if self._failures >= self._limit or self._opened_at is not None:
                self._opened_at = self._clock()

    @property
    def is_open(self) -> bool:
        with self._lock:
            return self._opened_at is not None


class GuardedLlm:
    """The model client behind a breaker. A failed call is not repeated; a paused one fails fast."""

    def __init__(self, inner, breaker: CircuitBreaker | None = None) -> None:
        self._inner = inner
        self._breaker = breaker or CircuitBreaker()
        self.model = inner.model

    def complete(
        self,
        system: str,
        user: str,
        max_output_tokens: int,
        json_schema: dict | None = None,
        on_delta=None,
    ) -> LlmResult:
        if not self._breaker.allow():
            raise LlmError("the model is paused after repeated failures")
        extra = {"on_delta": on_delta} if on_delta is not None else {}
        try:
            result = self._inner.complete(system, user, max_output_tokens, json_schema, **extra)
        except LlmError:
            self._breaker.record_failure()
            raise
        self._breaker.record_success()
        return result
