"""The internal search service: reply builders, routing and the HTTP wrapper.

No database and no model are used.
"""

import json
import logging
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from graphlens_pipeline.answer import AnswerResult, Passage
from graphlens_pipeline.globalsearch import GlobalAnswer, Selected
from graphlens_pipeline.localanswer import Check, LocalAnswer
from graphlens_pipeline.localcontext import ContextItem, LocalContext
from graphlens_pipeline.localgraph import Edge, Node, Subgraph
from graphlens_pipeline.relate import Hop, Path, RelateAnswer
from graphlens_pipeline.searchservice import (
    Backends,
    SearchService,
    build_baseline,
    build_global,
    build_local,
    build_relate,
    create_app,
)

# the fields of the API's `Answer` model (api/app/schemas.py); the API refuses a reply with others
ANSWER_FIELDS = {
    "mode", "status", "text", "message", "citations", "nodes", "links",
    "check_status", "model", "cost_usd", "latency_ms",
}  # fmt: skip
CITATION_FIELDS = {"label", "kind", "title", "text", "source", "ref_id"}
KEY = "a-long-shared-test-key"
MARKER = "SECRET-MARKER-5d1e"


def unit_rows(ids):
    return {i: {"text": f"text of {i}", "title": "Paper X", "section": "4 Results"} for i in ids}


def local_context():
    items = [
        ContextItem("T1", "unit", "u_1", "KGT5 uses T5-small.", 10),
        ContextItem("E2", "entity", "e_data", "Wikidata5M (Dataset): a knowledge graph", 8),
        ContextItem("T3", "unit", "u_3", "not cited", 5),
    ]
    graph = Subgraph(
        nodes=[
            Node("e_kgt5", "KGT5", "Method", "", [], 3, 0, is_seed=True, score=1.0),
            Node("e_data", "Wikidata5M", "Dataset", "", [], 2, 1, score=0.5),
        ],
        edges=[Edge("e_kgt5", "e_data", "EVALUATED_ON", "", 1.0, ["u_1"])],
    )
    context = LocalContext("q", items)
    context.graph = graph
    return context


def test_a_local_answer_becomes_text_citations_and_a_small_graph():
    check = Check("verified", cited=["T1", "E2", "T1"])
    text = "KGT5 is small [T1] and tested on Wikidata5M [E2]."
    answer = LocalAnswer("q", "answered", text=text, check=check, cost_usd=0.0035)
    reply = build_local(answer, local_context(), unit_rows)
    assert set(reply) == ANSWER_FIELDS
    assert reply["status"] == "answered" and reply["check_status"] == "verified"
    assert [c["label"] for c in reply["citations"]] == ["T1", "E2"]  # cited only, once each
    assert all(set(c) == CITATION_FIELDS for c in reply["citations"])
    assert (
        reply["citations"][0]["title"] == "Paper X"
        and reply["citations"][0]["source"] == "4 Results"
    )
    assert {n["id"] for n in reply["nodes"]} == {"e_kgt5", "e_data"}
    assert reply["links"] == [
        {"source": "e_kgt5", "target": "e_data", "predicate": "EVALUATED_ON", "confidence": None}
    ]
    assert reply["cost_usd"] == 0.0035


def test_a_label_the_context_does_not_have_is_left_out_of_the_sources():
    answer = LocalAnswer("q", "answered", text="x [T9]", check=Check("warning", cited=["T9"]))
    reply = build_local(answer, local_context(), unit_rows)
    assert reply["citations"] == [] and reply["check_status"] == "warning"


def test_a_local_refusal_and_a_clarify_question_carry_a_message():
    refused = LocalAnswer(
        "q", "refused", reason="No entity is close enough.", suggestion="Name a method."
    )
    reply = build_local(refused, None, unit_rows)
    assert (
        reply["status"] == "refused"
        and reply["message"] == "No entity is close enough. Name a method."
    )
    clarify = LocalAnswer(
        "q", "clarify", reason='"QA" can mean two things.', options=["QA model", "QA task"]
    )
    reply = build_local(clarify, None, unit_rows)
    assert reply["status"] == "clarify" and "QA model; QA task" in reply["message"]


def relate_answer(status="answered", **fields):
    path = Path(
        nodes=[
            {"id": "a", "name": "A", "type": "Method"},
            {"id": "b", "name": "B", "type": "Dataset"},
        ],
        hops=[Hop("a", "b", "EVALUATED_ON", "", ["u_1"])],
    )
    base = {
        "paths": [path],
        "text": "A is evaluated on B [T1].",
        "check": Check("verified", cited=["T1"]),
    }
    base.update(fields)
    answer = RelateAnswer("q", status, **base)
    answer.context = LocalContext("q", [ContextItem("T1", "unit", "u_1", "passage", 5)])
    return answer


def test_a_relate_answer_shows_the_best_path_as_the_graph():
    reply = build_relate(relate_answer(), unit_rows)
    assert set(reply) == ANSWER_FIELDS and reply["mode"] == "relate"
    assert [n["label"] for n in reply["nodes"]] == ["A", "B"]
    assert reply["links"][0]["predicate"] == "EVALUATED_ON"
    assert reply["citations"][0]["label"] == "T1"


def test_relate_without_a_path_or_with_a_clarify_question_is_a_plain_message():
    none = relate_answer("no_path", paths=[], text="", reason="No path joins A and B.",
                         shared_communities=[{"title": "Retrieval methods"}])  # fmt: skip
    reply = build_relate(none, unit_rows)
    assert reply["status"] == "refused" and "Retrieval methods" in reply["message"]
    clarify = relate_answer("clarify", paths=[], text="", reason="Which A?", options=["A1", "A2"])
    assert build_relate(clarify, unit_rows)["status"] == "clarify"


def test_a_global_answer_cites_community_reports():
    used = [Selected("c1", "Retrieval trends", "A summary.", ["finding one"], 0.8, "C1")]
    reply = build_global(
        GlobalAnswer("q", text="Many papers study retrieval [C1].", used=used, cost_usd=0.01)
    )
    assert set(reply) == ANSWER_FIELDS and reply["mode"] == "global"
    assert reply["citations"][0]["kind"] == "community" and reply["citations"][0]["label"] == "C1"
    assert reply["cost_usd"] == 0.01
    assert build_global(GlobalAnswer("q", text=""))["status"] == "refused"


def passage(n):
    return Passage(n, f"u_{n}", f"text {n}", "3 Method", "Paper Y", "p1", 0.5)


def test_a_plain_rag_answer_gets_t_labels_so_the_screen_can_show_chips():
    passages = [passage(n) for n in (1, 2, 3, 4)]
    result = AnswerResult(
        "q", "It works [1][3] and more [1, 2].", False, passages,
        cited=[1, 2, 3], citations_valid=True, model="gpt-4.1-mini", cost_usd=0.001,
    )  # fmt: skip
    reply = build_baseline(result)
    assert reply["text"] == "It works [T1][T3] and more [T1][T2]."
    assert [c["label"] for c in reply["citations"]] == ["T1", "T2", "T3"]  # passage 4 was not cited
    assert reply["check_status"] == "verified" and reply["model"] == "gpt-4.1-mini"
    bad = AnswerResult("q", "x [1]", False, [passage(1)], cited=[1], citations_valid=False)
    assert build_baseline(bad)["check_status"] == "warning"
    plain = AnswerResult("q", "no citations", False, [passage(1)], cited=[])
    assert build_baseline(plain)["check_status"] == "not_checked"
    refusal = build_baseline(AnswerResult("q", "Not enough evidence.", True, []))
    assert refusal["status"] == "refused" and refusal["message"] == "Not enough evidence."


# ---------------------------------------------------------------- the service


def reply(mode, cost=0.01):
    return {
        "mode": mode, "status": "answered", "text": "t", "message": None,
        "citations": [], "nodes": [], "links": [], "check_status": "not_checked",
        "model": "", "cost_usd": cost, "latency_ms": 0,
    }  # fmt: skip


def backends(mode="local", router_cost=0.0, seen=None):
    seen = seen if seen is not None else []

    def run(name):
        def inner(question):
            seen.append(name)
            return reply(name)

        return inner

    route = SimpleNamespace(
        mode=mode, source="rules", confidence=0.9, ran_as_fallback=False, cost_usd=router_cost
    )
    return Backends(
        lambda q: route, run("local"), run("relate"), run("global"), run("baseline")
    ), seen


@pytest.mark.parametrize("mode", ["local", "relate", "global", "baseline"])
def test_the_service_runs_the_mode_the_router_chose(mode):
    b, seen = backends(mode)
    out = SearchService(b, model="m").ask("q", compare=False)
    assert seen == [mode] and out["answer"]["mode"] == mode and out["baseline"] is None
    assert out["route"] == {"mode": mode, "source": "rules", "confidence": 0.9, "fallback": False}
    assert out["answer"]["model"] == "m" and out["answer"]["latency_ms"] >= 0


def test_compare_adds_a_plain_rag_answer_but_not_a_second_one_for_baseline_mode():
    b, seen = backends("local")
    out = SearchService(b).ask("q", compare=True)
    assert seen == ["local", "baseline"] and out["baseline"]["mode"] == "baseline"
    b, seen = backends("baseline")
    assert SearchService(b).ask("q", compare=True)["baseline"] is None and seen == ["baseline"]


def test_the_router_model_cost_is_added_to_the_answer_cost():
    b, _ = backends("local", router_cost=0.0004)
    assert SearchService(b).ask("q", False)["answer"]["cost_usd"] == pytest.approx(0.0104)


# ---------------------------------------------------------------- the HTTP wrapper


class FakeService:
    def __init__(self, error=None):
        self.error, self.calls = error, []

    def ask(self, question, compare):
        self.calls.append((question, compare))
        if self.error:
            raise self.error
        return {"answer": reply("local"), "baseline": None, "route": {}}


def client(service):
    return TestClient(create_app(lambda: service, KEY), raise_server_exceptions=False)


def post(c, body, key=KEY, **headers):
    sent = dict(headers)
    if key is not None:
        sent["X-Search-Key"] = key
    return c.post("/search", json=body, headers=sent)


def test_the_service_needs_the_shared_key():
    with client(FakeService()) as c:
        assert post(c, {"question": "Hi"}, key=None).status_code == 401
        assert post(c, {"question": "Hi"}, key="wrong").status_code == 401
        assert post(c, {"question": "Hi"}).status_code == 200


def test_an_empty_shared_key_means_every_request_is_refused():
    app = create_app(lambda: FakeService(), "")
    with TestClient(app) as c:
        assert (
            c.post("/search", json={"question": "Hi"}, headers={"X-Search-Key": ""}).status_code
            == 401
        )


def test_the_question_is_trimmed_and_compare_is_passed_on():
    service = FakeService()
    with client(service) as c:
        body = post(c, {"question": "  Hi  ", "compare": True}).json()
    assert service.calls == [("Hi", True)] and body["answer"]["mode"] == "local"


@pytest.mark.parametrize(
    "body", [{}, {"question": ""}, {"question": "x" * 4001}, {"question": "ok", "extra": 1}]
)
def test_bad_requests_are_refused_without_echoing_them(body):
    with client(FakeService()) as c:
        response = post(c, body)
    assert response.status_code == 422 and "xxxx" not in response.text


def test_health_is_ok_once_the_service_has_started():
    with client(FakeService()) as c:
        assert c.get("/healthz").json() == {"status": "ok"}


def test_an_unexpected_error_is_a_plain_500_and_the_question_is_never_logged(caplog):
    caplog.set_level(logging.INFO)
    with client(FakeService(error=RuntimeError(f"boom {MARKER}"))) as c:
        response = post(c, {"question": f"hello {MARKER}"}, **{"X-Request-Id": "req-12345678"})
    assert response.status_code == 500 and response.json()["error"]["code"] == "search_failed"
    ours = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("graphlens"))
    assert MARKER not in ours and "RuntimeError" in ours and "req-12345678" in ours


def test_a_successful_request_is_logged_without_the_question(caplog):
    caplog.set_level(logging.INFO)
    with client(FakeService()) as c:
        post(c, {"question": f"hello {MARKER}"})
    ours = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("graphlens"))
    assert "mode=local" in ours and MARKER not in ours


def test_the_reply_is_valid_json_with_exactly_the_documented_answer_fields():
    with client(FakeService()) as c:
        body = json.loads(post(c, {"question": "Hi"}).text)
    assert set(body) == {"answer", "baseline", "route"} and set(body["answer"]) == ANSWER_FIELDS


# ---------------------------------------------------------------- slots and the deadline


class SlowService:
    """A service whose question runs until the test lets it go."""

    def __init__(self):
        import threading

        self.release = threading.Event()
        self.started = threading.Event()

    def ask(self, question, compare):
        self.started.set()
        self.release.wait(5)
        return {"answer": reply("local"), "baseline": None, "route": {}}


def test_a_question_that_runs_too_long_gets_504_and_keeps_its_slot_until_it_really_ends():
    slow = SlowService()
    app = create_app(lambda: slow, KEY, max_concurrent=1, queue_wait=0.1, deadline=0.2)
    with TestClient(app, raise_server_exceptions=False) as c:
        first = post(c, {"question": "slow one"})
        assert first.status_code == 504 and first.json()["error"]["code"] == "search_timeout"
        # the stuck question still holds the only slot, so the next one is told "busy" at once
        second = post(c, {"question": "next"})
        assert second.status_code == 503 and second.json()["error"]["code"] == "busy"
        slow.release.set()  # the stuck question finishes; the slot is free again
        for _ in range(50):
            if post(c, {"question": "after"}).status_code == 200:
                break
            time.sleep(0.05)
        else:
            raise AssertionError("the slot was never released")


def test_the_gate_lets_as_many_questions_run_at_once_as_there_are_slots():
    import threading

    active, peak, lock = 0, 0, threading.Lock()

    class Counting:
        def ask(self, question, compare):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.15)
            with lock:
                active -= 1
            return {"answer": reply("local"), "baseline": None, "route": {}}

    app = create_app(lambda: Counting(), KEY, max_concurrent=2, queue_wait=5, deadline=5)
    with TestClient(app) as c:
        results = []
        threads = [
            threading.Thread(target=lambda: results.append(post(c, {"question": "q"}).status_code))
            for _ in range(6)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert results == [200] * 6 and peak <= 2
