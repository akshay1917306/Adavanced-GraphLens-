"""Replay service on the real saved file, plus the examples endpoint."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import ask as ask_module
from app import main
from app import visitor as visitor_module
from app.replay import ReplayService
from app.schemas import AskResponse


@pytest.fixture
def service():
    return ReplayService()


def test_every_saved_answer_is_valid_and_cites_only_what_it_shows(service):
    assert len(service.examples()) >= 5
    for question in service.examples():
        response = service.ask(question, compare=True)
        assert isinstance(response, AskResponse) and response.fixture
        answer = response.answer
        if answer.status == "answered":
            shown = {c.label for c in answer.citations}
            assert shown, question
            node_ids = {n.id for n in answer.nodes}
            assert all(link.source in node_ids and link.target in node_ids for link in answer.links)
            assert 2 <= len(answer.nodes) <= 6
            assert response.baseline and response.baseline.mode == "baseline"
        else:
            assert answer.message


def test_question_matching_ignores_case_and_spacing(service):
    question = service.examples()[0]
    messy = "  " + question.upper().replace(" ", "   ") + " "
    assert service.ask(messy, False).answer.status == "answered"


def test_unknown_question_gets_a_plain_refusal_not_an_invented_answer(service):
    response = service.ask("Who invented the telephone?", compare=True)
    assert response.answer.status == "refused"
    assert response.answer.text == ""
    assert response.baseline is None


def test_the_api_serves_replay_answers_and_the_example_list(service, monkeypatch):
    main.app.dependency_overrides[ask_module.get_ask_service] = lambda: service
    main.app.dependency_overrides[main.get_store] = lambda: _NoStore()
    main.app.dependency_overrides[visitor_module.get_visitor] = lambda: uuid4()
    try:
        client = TestClient(main.app)
        questions = client.get("/api/v1/examples").json()["questions"]
        body = client.post("/api/v1/ask", json={"question": questions[0], "compare": True}).json()
    finally:
        main.app.dependency_overrides.clear()
    assert body["fixture"] is True
    assert body["answer"]["check_status"] == "verified"
    assert body["baseline"]["mode"] == "baseline"


class _NoStore:
    def save_answer(self, visitor_id, question, answer, index_version):
        return "33333333-3333-3333-3333-333333333333"
