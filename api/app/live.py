"""Live answers: the API asks the internal search service (CR-0004) and returns its reply.

The service is reachable only inside the Compose network and every call carries a shared key. A
call has a hard time limit. It is retried once only when the connection could not even be opened,
never after the request was sent, so a paid answer is never repeated by accident. After repeated
failures a circuit breaker makes calls fail at once for a short while.
"""

import json
import logging
import time
from collections.abc import Iterator
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.ask import EngineUnavailable
from app.breaker import CircuitBreaker
from app.hardening import request_id_var
from app.replay import ReplayService
from app.schemas import Answer, AskResponse

log = logging.getLogger("graphlens.live")

CONNECT_RETRY_PAUSE = 0.3


class EngineTimeout(Exception):
    """The search service did not answer in time."""


class StrictAnswer(Answer):
    """An answer from the service. A field the API does not know is a bug on one of the sides."""

    model_config = ConfigDict(extra="forbid")


class SearchReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: StrictAnswer
    baseline: StrictAnswer | None = None
    route: dict | None = None


class LiveService:
    live = True

    def __init__(
        self,
        url: str,
        key: str,
        timeout_seconds: float = 45.0,
        client: httpx.Client | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        if not url or not key:
            raise RuntimeError("ANSWER_MODE=live needs SEARCH_SERVICE_URL and SEARCH_SERVICE_KEY")
        self._key = key
        self._breaker = breaker or CircuitBreaker()
        self._client = client or httpx.Client(
            base_url=url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds, connect=3.0, write=5.0),
        )
        self._examples = ReplayService().examples()  # suggestions only; any question can be asked

    def examples(self) -> list[str]:
        return list(self._examples)

    def _post(self, question: str, compare: bool) -> httpx.Response:
        headers = {"X-Search-Key": self._key, "X-Request-Id": request_id_var.get()}
        body = {"question": question, "compare": compare}
        try:
            return self._client.post("/search", json=body, headers=headers)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            time.sleep(CONNECT_RETRY_PAUSE)  # nothing was sent, so one more try cannot double-spend
            return self._client.post("/search", json=body, headers=headers)

    def _response(self, reply: SearchReply) -> AskResponse:
        return AskResponse(
            answer_id=uuid4().hex,
            answer=Answer(**reply.answer.model_dump()),
            baseline=Answer(**reply.baseline.model_dump()) if reply.baseline else None,
            fixture=False,
        )

    def open_stream(self, question: str, compare: bool, timeout_seconds: float = 45.0):
        """Open the streaming call. Problems before the first byte raise like `ask` does, so the
        route can still answer with a proper HTTP status. Returns an iterator of
        ("delta", text), then ("final", AskResponse); a failure in the middle raises."""
        if not self._breaker.allow():
            raise EngineUnavailable("the search service is paused after repeated failures")
        headers = {"X-Search-Key": self._key, "X-Request-Id": request_id_var.get()}
        request = self._client.build_request(
            "POST",
            "/search/stream",
            json={"question": question, "compare": compare},
            headers=headers,
        )
        try:
            try:
                response = self._client.send(request, stream=True)
            except (httpx.ConnectError, httpx.ConnectTimeout):
                time.sleep(CONNECT_RETRY_PAUSE)  # nothing was sent yet
                response = self._client.send(request, stream=True)
        except httpx.TimeoutException as error:
            self._breaker.record_failure()
            raise EngineTimeout from error
        except httpx.HTTPError as error:
            self._breaker.record_failure()
            log.error("search service unreachable %s", type(error).__name__)
            raise EngineUnavailable("the search service cannot be reached") from error
        if response.status_code != 200:
            response.close()
            self._breaker.record_failure()
            if response.status_code == 504:
                raise EngineTimeout
            log.error("search service answered %s", response.status_code)
            raise EngineUnavailable(f"the search service answered {response.status_code}")
        return self._events(response, timeout_seconds)

    def _events(self, response: httpx.Response, timeout_seconds: float) -> Iterator[tuple]:
        ends = time.monotonic() + timeout_seconds
        finished = False
        try:
            for line in response.iter_lines():
                if time.monotonic() > ends:
                    raise EngineTimeout
                if not line:
                    continue
                code = ""
                try:
                    event = json.loads(line)
                    kind = event["type"]
                    if kind == "delta":
                        yield "delta", str(event["text"])
                        continue
                    if kind == "final":
                        reply = SearchReply.model_validate(event["reply"])
                        finished = True
                        self._breaker.record_success()
                        yield "final", self._response(reply)
                        return
                    if kind == "error":
                        code = str(event.get("code", ""))
                except (ValueError, KeyError, TypeError, ValidationError) as error:
                    log.error("search service stream not understood (%s)", type(error).__name__)
                    raise EngineUnavailable("the search service reply is not understood") from error
                if code == "search_timeout":
                    raise EngineTimeout
                raise EngineUnavailable("the search service failed")
            raise EngineUnavailable("the search service stream ended early")
        except (EngineTimeout, EngineUnavailable):
            if not finished:
                self._breaker.record_failure()
            raise
        except httpx.TimeoutException as error:
            self._breaker.record_failure()
            raise EngineTimeout from error
        except httpx.HTTPError as error:
            self._breaker.record_failure()
            raise EngineUnavailable("the search service stream broke") from error
        finally:
            response.close()

    def ask(self, question: str, compare: bool) -> AskResponse:
        if not self._breaker.allow():
            raise EngineUnavailable("the search service is paused after repeated failures")
        try:
            response = self._post(question, compare)
        except httpx.TimeoutException as error:
            self._breaker.record_failure()
            log.error("search service timed out %s", type(error).__name__)
            raise EngineTimeout from error
        except httpx.HTTPError as error:
            self._breaker.record_failure()
            log.error("search service unreachable %s", type(error).__name__)
            raise EngineUnavailable("the search service cannot be reached") from error
        if response.status_code == 504:
            # the search service gave up on its own deadline: same message as our own time limit
            self._breaker.record_failure()
            raise EngineTimeout
        if response.status_code != 200:
            # 401 is a wrong shared key, 5xx a broken or still starting service: all are failures
            self._breaker.record_failure()
            log.error("search service answered %s", response.status_code)
            raise EngineUnavailable(f"the search service answered {response.status_code}")
        try:
            reply = SearchReply.model_validate_json(response.content)
        except ValidationError as error:
            self._breaker.record_failure()
            log.error(
                "search service reply did not match the contract (%d problems)", error.error_count()
            )
            raise EngineUnavailable("the search service reply is not understood") from error
        self._breaker.record_success()
        return self._response(reply)
