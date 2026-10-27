"""Rate limits and the daily cost cap, kept in Redis (D53).

Fixed windows: every request adds one to a counter that lives for one window. Over the limit the
request is refused with 429 and `Retry-After`. If Redis cannot be reached the request is refused
(fail closed): a limiter that silently stops limiting is worse than a short outage.

The client address comes from the web server in `X-Client-Ip`, and only when the request also
carries the shared `X-Proxy-Secret`; a direct caller cannot choose its own address.
"""

import hmac
import time
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import redis
from fastapi import Depends, Header, Request

from app.config import get_settings
from app.visitor import get_visitor


class RateLimited(Exception):
    def __init__(self, retry_after: int, what: str = "requests") -> None:
        super().__init__(what)
        self.retry_after = max(1, retry_after)
        self.what = what


class LimiterUnavailable(Exception):
    """Redis could not be reached, so nothing can be counted."""


class DailyCapReached(Exception):
    """The money spent on model calls today has reached the cap."""


class Limiter:
    def __init__(self, client) -> None:
        self._client = client

    def hit(self, scope: str, key: str, limit: int, window_seconds: int) -> None:
        """Count one request; raise RateLimited when this window's limit is passed."""
        now = int(time.time())
        name = f"rl:{scope}:{key}:{now // window_seconds}"
        try:
            pipe = self._client.pipeline()
            pipe.incr(name)
            pipe.expire(name, window_seconds + 1)
            count = pipe.execute()[0]
        except redis.RedisError as error:
            raise LimiterUnavailable from error
        if count > limit:
            raise RateLimited(window_seconds - now % window_seconds)

    def spent_today(self) -> float:
        try:
            return float(self._client.get(self._cost_key()) or 0)
        except redis.RedisError as error:
            raise LimiterUnavailable from error

    def ensure_room(self, cap_usd: float) -> None:
        if self.spent_today() >= cap_usd:
            raise DailyCapReached

    def record_cost(self, usd: float) -> None:
        if usd <= 0:
            return
        try:
            key = self._cost_key()
            self._client.incrbyfloat(key, usd)
            self._client.expire(key, 2 * 86400)
        except redis.RedisError as error:
            raise LimiterUnavailable from error

    @staticmethod
    def _cost_key() -> str:
        return f"cost:{datetime.now(UTC).date().isoformat()}"


@lru_cache
def get_limiter() -> Limiter:
    client = redis.Redis.from_url(
        get_settings().redis_url, socket_timeout=1, socket_connect_timeout=1
    )
    return Limiter(client)


def client_ip(
    request: Request,
    x_client_ip: Annotated[str | None, Header()] = None,
    x_proxy_secret: Annotated[str | None, Header()] = None,
) -> str:
    secret = get_settings().proxy_secret.get_secret_value()
    if secret and x_proxy_secret and x_client_ip and hmac.compare_digest(x_proxy_secret, secret):
        return x_client_ip[:64]
    return request.client.host if request.client else "unknown"


def visitor_creation_limit(
    ip: Annotated[str, Depends(client_ip)],
    limiter: Annotated[Limiter, Depends(get_limiter)],
) -> None:
    limiter.hit("visitor-new", ip, get_settings().rate_visitor_ip_per_min, 60)


def current_visitor(
    visitor: Annotated[UUID, Depends(get_visitor)],
    limiter: Annotated[Limiter, Depends(get_limiter)],
) -> UUID:
    """The visitor of this request, after the general per-visitor limit."""
    limiter.hit("general", str(visitor), get_settings().rate_general_per_min, 60)
    return visitor


def ask_limits(
    visitor: Annotated[UUID, Depends(current_visitor)],
    ip: Annotated[str, Depends(client_ip)],
    limiter: Annotated[Limiter, Depends(get_limiter)],
) -> None:
    """Extra limits for the expensive route, plus the daily cost cap."""
    settings = get_settings()
    limiter.hit("ask-min", str(visitor), settings.rate_ask_per_min, 60)
    limiter.hit("ask-day", str(visitor), settings.rate_ask_per_day, 86400)
    limiter.hit("ask-ip", ip, settings.rate_ask_ip_per_min, 60)
    limiter.ensure_room(settings.daily_cost_cap_usd)
