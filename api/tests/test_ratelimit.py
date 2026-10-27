"""Rate limits and the daily cost cap, with an in-memory Redis stand-in."""

from uuid import uuid4

import pytest
import redis
from fastapi.testclient import TestClient

from app import ask as ask_module
from app import main
from app import ratelimit as rl
from app import visitor as visitor_module
from app.config import Settings
from app.schemas import Answer, AskResponse


class FakeRedis:
    """Just enough of Redis for the limiter: counters, expiry marks, floats."""

    def __init__(self, down: bool = False):
        self.data: dict[str, float] = {}
        self.expiry: dict[str, int] = {}
        self.down = down

    def pipeline(self):
        outer = self

        class Pipe:
            def __init__(self):
                self.ops = []

            def incr(self, name):
                self.ops.append(("incr", name))

            def expire(self, name, seconds):
                self.ops.append(("expire", name, seconds))

            def execute(self):
                if outer.down:
                    raise redis.ConnectionError("down")
                out = []
                for op in self.ops:
                    if op[0] == "incr":
                        outer.data[op[1]] = outer.data.get(op[1], 0) + 1
                        out.append(int(outer.data[op[1]]))
                    else:
                        outer.expiry[op[1]] = op[2]
                        out.append(True)
                return out

        return Pipe()

    def get(self, name):
        if self.down:
            raise redis.ConnectionError("down")
        return self.data.get(name)

    def incrbyfloat(self, name, amount):
        self.data[name] = self.data.get(name, 0) + amount

    def expire(self, name, seconds):
        self.expiry[name] = seconds


def test_the_limit_counts_and_then_refuses_with_a_wait_time():
    limiter = rl.Limiter(FakeRedis())
    for _ in range(3):
        limiter.hit("x", "a", 3, 60)
    with pytest.raises(rl.RateLimited) as caught:
        limiter.hit("x", "a", 3, 60)
    assert 1 <= caught.value.retry_after <= 60


def test_different_keys_and_scopes_do_not_share_a_counter():
    limiter = rl.Limiter(FakeRedis())
    limiter.hit("x", "a", 1, 60)
    limiter.hit("x", "b", 1, 60)
    limiter.hit("y", "a", 1, 60)
    with pytest.raises(rl.RateLimited):
        limiter.hit("x", "a", 1, 60)


def test_a_new_window_starts_at_zero(monkeypatch):
    limiter = rl.Limiter(FakeRedis())
    monkeypatch.setattr(rl.time, "time", lambda: 1000.0)
    limiter.hit("x", "a", 1, 60)
    with pytest.raises(rl.RateLimited):
        limiter.hit("x", "a", 1, 60)
    monkeypatch.setattr(rl.time, "time", lambda: 1000.0 + 61)
    limiter.hit("x", "a", 1, 60)  # the next window: allowed again


def test_when_redis_is_down_the_request_is_refused_not_waved_through():
    limiter = rl.Limiter(FakeRedis(down=True))
    with pytest.raises(rl.LimiterUnavailable):
        limiter.hit("x", "a", 5, 60)


def test_the_daily_cap_stops_further_answers():
    limiter = rl.Limiter(FakeRedis())
    limiter.ensure_room(1.0)
    limiter.record_cost(0.6)
    limiter.ensure_room(1.0)
    limiter.record_cost(0.5)
    with pytest.raises(rl.DailyCapReached):
        limiter.ensure_room(1.0)
    limiter.record_cost(0)  # a free answer adds nothing


class PaidService:
    """A fake model that costs 0.6 dollars per answer."""

    def ask(self, question, compare):
        answer = Answer(mode="local", status="answered", text="ok", cost_usd=0.6)
        return AskResponse(answer_id="a", answer=answer)


class FakeStore:
    def visitor_exists(self, visitor_id):
        return True

    def save_answer(self, visitor_id, question, answer, index_version):
        return str(uuid4())


@pytest.fixture
def make(monkeypatch):
    def build(limiter, **settings):
        s = Settings(visitor_token_secret="s", **settings)
        for module in (main, visitor_module, rl):
            monkeypatch.setattr(module, "get_settings", lambda: s)
        main.app.dependency_overrides[rl.get_limiter] = lambda: limiter
        main.app.dependency_overrides[main.get_store] = lambda: FakeStore()
        main.app.dependency_overrides[ask_module.get_ask_service] = lambda: PaidService()
        visitor = uuid4()
        main.app.dependency_overrides[visitor_module.get_visitor] = lambda: visitor
        return TestClient(main.app, raise_server_exceptions=False)

    yield build
    main.app.dependency_overrides.clear()


def test_ask_is_limited_per_minute_with_retry_after(make):
    client = make(rl.Limiter(FakeRedis()), rate_ask_per_min=2, daily_cost_cap_usd=99.0)
    for _ in range(2):
        assert client.post("/api/v1/ask", json={"question": "Hi"}).status_code == 200
    third = client.post("/api/v1/ask", json={"question": "Hi"})
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "rate_limited"
    assert int(third.headers["Retry-After"]) >= 1


def test_the_daily_cap_refuses_after_the_money_is_spent(make):
    client = make(rl.Limiter(FakeRedis()), daily_cost_cap_usd=1.0)
    assert client.post("/api/v1/ask", json={"question": "Hi"}).status_code == 200  # 0.6 spent
    assert client.post("/api/v1/ask", json={"question": "Hi"}).status_code == 200  # 1.2 spent
    refused = client.post("/api/v1/ask", json={"question": "Hi"})
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "daily_limit"


def test_other_routes_have_a_general_limit_per_visitor(make):
    client = make(rl.Limiter(FakeRedis()), rate_general_per_min=2)
    codes = [client.get("/api/v1/preferences").status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_creating_visitors_is_limited_per_address(make):
    store = FakeStore()
    store.create_visitor = lambda: uuid4()
    main.app.dependency_overrides[main.get_store] = lambda: store
    client = make(rl.Limiter(FakeRedis()), rate_visitor_ip_per_min=2)
    main.app.dependency_overrides[main.get_store] = lambda: store
    codes = [client.post("/api/v1/visitor", json={}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_when_the_limiter_is_down_ask_is_refused(make):
    client = make(rl.Limiter(FakeRedis(down=True)))
    response = client.post("/api/v1/ask", json={"question": "Hi"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "limiter_unavailable"


def test_the_client_address_is_trusted_only_with_the_shared_secret(monkeypatch):
    monkeypatch.setattr(rl, "get_settings", lambda: Settings(proxy_secret="shared"))

    class Req:
        class client:  # noqa: N801
            host = "172.18.0.1"

    assert rl.client_ip(Req, "203.0.113.5", "shared") == "203.0.113.5"
    assert rl.client_ip(Req, "203.0.113.5", "wrong") == "172.18.0.1"
    assert rl.client_ip(Req, "203.0.113.5", None) == "172.18.0.1"
    assert rl.client_ip(Req, None, "shared") == "172.18.0.1"
