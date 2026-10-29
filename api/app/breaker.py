"""A circuit breaker for the search service (CR-0004).

After several failures in a row the breaker opens and calls fail at once for a while instead of
waiting for a timeout each time. After the pause one trial call is let through: if it works the
breaker closes, if it fails the pause starts again.
"""

import threading
import time
from collections.abc import Callable


class CircuitBreaker:
    def __init__(
        self,
        failures: int = 5,
        pause_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = failures
        self._pause = pause_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at: float | None = None
        self._trial_running = False

    def allow(self) -> bool:
        """True when a call may go out. While open, one trial call is allowed after the pause."""
        with self._lock:
            if self._opened_at is None:
                return True
            if self._clock() - self._opened_at < self._pause or self._trial_running:
                return False
            self._trial_running = True
            return True

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None
            self._trial_running = False

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
