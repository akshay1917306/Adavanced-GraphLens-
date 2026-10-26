"""The ask endpoint with a fake engine: validation, refusal as 200, error shapes."""

import pytest
from fastapi.testclient import TestClient

from app import ask as ask_module
from app import main
from app.schemas import Answer, AskResponse, Citation

URL = "/api/v1/ask"
ORIGIN = "http://localhost:3000"


class FakeService:
    def __init__(self, answer: Answer | None = None, error: Exception | None = None):
        self.calls: list[tuple[str, bool]] = []
        self._answer = answer or Answer(mode="local", status="answered", text="ok")
        self._error = error

    def ask(self, question: str, compare: bool) -> AskResponse:
        self.calls.append((question, compare))
        if self._error:
            raise self._error
        baseline = self._answer.model_copy(update={"mode": "baseline"}) if compare else None
        return AskResponse(answer_id="a1", answer=self._answer, baseline=baseline, fixture=True)


@pytest.fixture
def client():
    def make(service):
        main.app.dependency_overrides[ask_module.get_ask_service] = lambda: service
        return TestClient(main.app, raise_server_exceptions=False)

    yield make
    main.app.dependency_overrides.clear()


def test_answer_has_the_documented_shape(client):
    answer = Answer(
        mode="local",
        status="answered",
        text="X improves on Y [T1].",
        citations=[Citation(label="T1", kind="text_unit", title="Paper", text="passage")],
        check_status="verified",
    )
    body = client(FakeService(answer)).post(URL, json={"question": "  What?  "}).json()
    assert body["answer"]["citations"][0]["label"] == "T1"
    assert body["answer"]["check_status"] == "verified"
    assert body["baseline"] is None
    assert body["fixture"] is True


def test_question_is_trimmed_and_compare_is_passed(client):
    service = FakeService()
    body = client(service).post(URL, json={"question": "  Hi  ", "compare": True}).json()
    assert service.calls == [("Hi", True)]
    assert body["baseline"]["mode"] == "baseline"


def test_a_refusal_is_a_normal_answer(client):
    refusal = Answer(mode="local", status="refused", message="No matching entity.")
    response = client(FakeService(refusal)).post(URL, json={"question": "Capital of France?"})
    assert response.status_code == 200
    assert response.json()["answer"]["status"] == "refused"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": ""},
        {"question": "   "},
        {"question": 5},
        {"question": "x" * 4001},
        {"question": "ok", "extra": 1},
    ],
)
def test_bad_requests_are_rejected_without_echoing_input(client, payload):
    response = client(FakeService()).post(URL, json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert "xxxx" not in response.text


def test_secret_in_a_rejected_request_is_not_echoed(client):
    payload = {"question": "sk-abcdefghijklmnopqrstuvwx", "n": 1}
    response = client(FakeService()).post(URL, json=payload)
    assert response.status_code == 422
    assert "sk-abcdefgh" not in response.text


def test_unconfigured_engine_is_503(client):
    response = client(ask_module.UnconfiguredService()).post(URL, json={"question": "Hi"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "engine_unavailable"


def test_unexpected_error_hides_details(client):
    service = FakeService(error=RuntimeError("secret detail /app/x.py"))
    response = client(service).post(URL, json={"question": "Hi"})
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Something went wrong."}
    }


def test_cors_allows_only_the_web_origin(client):
    c = client(FakeService())
    method = {"Access-Control-Request-Method": "POST"}
    ok = c.options(URL, headers={"Origin": ORIGIN, **method})
    bad = c.options(URL, headers={"Origin": "http://evil.example", **method})
    assert ok.headers.get("access-control-allow-origin") == ORIGIN
    assert "access-control-allow-origin" not in bad.headers
