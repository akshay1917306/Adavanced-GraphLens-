"""The answer engine behind POST /api/v1/ask.

The API only depends on the `AskService` protocol. Implementations: the replay service
(saved answers, no model, no key) and the live service (app/live.py) that asks the internal
search service. With no service configured the endpoint reports "unavailable".
"""

from typing import Protocol

from app.schemas import AskResponse


class EngineUnavailable(Exception):
    """No answer engine is configured or it cannot be reached."""


class AskService(Protocol):
    def ask(self, question: str, compare: bool) -> AskResponse: ...


class UnconfiguredService:
    def ask(self, question: str, compare: bool) -> AskResponse:
        raise EngineUnavailable("no answer engine is configured")


_service: AskService = UnconfiguredService()


def get_ask_service() -> AskService:
    return _service


def set_ask_service(service: AskService) -> None:
    global _service
    _service = service
