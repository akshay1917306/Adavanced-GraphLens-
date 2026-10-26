"""Tests for the router. The classifier model is a labelled MOCK; rules need no model."""

from __future__ import annotations

import json

import pytest

from graphlens_pipeline.linking import EntityIndex
from graphlens_pipeline.llm import LlmError, LlmResult
from graphlens_pipeline.router import (
    FALLBACK_BELOW,
    MODES,
    classify_with_model,
    route_by_rules,
    route_question,
)


def ent(eid, name, type_="Method", aliases=(), mentions=5):
    return {
        "id": eid, "name": name, "type": type_, "aliases": list(aliases), "mentions": mentions,
        "sources": [f"u_{eid}_0001"],
    }  # fmt: skip


INDEX = EntityIndex(
    [
        ent("f", "FiD", mentions=9),
        ent("n", "Natural Questions", "Dataset", aliases=["NQ"]),
        ent("d", "DPR"),
        ent("h", "HotpotQA", "Dataset"),
    ]
)


class MockRouterLlm:
    """MOCK classifier: returns a fixed mode and confidence, counts calls, can fail."""

    model = "gpt-4.1-mini"

    def __init__(self, mode="global", confidence=0.9, error=None, text=None):
        self.mode, self.confidence, self.error, self.text = mode, confidence, error, text
        self.calls = 0

    def complete(self, system, user, max_output_tokens, json_schema=None):
        self.calls += 1
        if self.error:
            raise self.error
        body = self.text or json.dumps({"mode": self.mode, "confidence": self.confidence})
        return LlmResult(body, self.model, 120, 15)


@pytest.mark.parametrize(
    ("question", "mode"),
    [
        ("How is FiD related to Natural Questions?", "relate"),
        ("What connects DPR and HotpotQA?", "relate"),
        ("What are the main research directions in this corpus?", "global"),
        ("Which papers work with knowledge graphs, and for which tasks?", "global"),
        ("Which methods improve on FiD and on which datasets were they evaluated?", "local"),
        ("What did the authors of the FiD paper change to make it faster at test time?", "local"),
        ("What is FiD?", "baseline"),
    ],
)
def test_the_rules_pick_the_expected_mode_without_a_model(question, mode):
    route = route_question(question, INDEX)
    assert route.mode == mode and route.source == "rules" and not route.asked_model


def test_confidences_follow_how_clear_the_signal_is():
    assert route_by_rules("How is FiD related to NQ?", INDEX).confidence == 0.9
    assert route_by_rules("What is FiD?", INDEX).confidence == 0.7
    assert route_by_rules("Hello there friend", INDEX).confidence == 0.4


def test_corpus_wide_wording_with_several_named_things_runs_as_local_with_a_note():
    route = route_question("Overall, how do FiD and DPR differ on HotpotQA?", INDEX)
    assert route.mode == "local" and route.ran_as_fallback and "runs as local" in route.reason


def test_a_relate_question_that_names_one_thing_is_unsure_and_falls_back():
    route = route_question("How is it related to anything?", INDEX)
    assert route.mode == "local" and route.ran_as_fallback and route.confidence < FALLBACK_BELOW


# --- the model is asked only when the rules are unsure ------------------------------------------


def test_a_clear_question_never_calls_the_model():
    llm = MockRouterLlm()
    assert route_question("How is FiD related to NQ?", INDEX, llm).source == "rules"
    assert llm.calls == 0


def test_an_unsure_question_asks_the_model_and_takes_a_more_confident_answer():
    llm = MockRouterLlm("global", 0.9)
    route = route_question("Hello there friend", INDEX, llm)
    assert llm.calls == 1 and route.mode == "global" and route.source == "model"
    assert route.asked_model and route.cost_usd > 0


def test_a_less_confident_model_does_not_overrule_the_rules():
    llm = MockRouterLlm("global", 0.2)
    route = route_question("Hello there friend", INDEX, llm)
    assert route.source == "rules" and route.asked_model and route.mode == "local"


def test_a_broken_or_failing_model_leaves_the_rules_in_charge():
    for llm in (
        MockRouterLlm(error=LlmError("model call failed (APIConnectionError)")),
        MockRouterLlm(text="not json"),
        MockRouterLlm(mode="teleport", confidence=0.9),
        MockRouterLlm(mode="local", confidence=7),
    ):
        route = route_question("Hello there friend", INDEX, llm)
        assert route.source == "rules" and route.mode == "local"
    with pytest.raises(LlmError):
        classify_with_model(MockRouterLlm(text="{}"), "x")


# --- the manual override -----------------------------------------------------------------------


def test_the_user_can_force_any_mode_and_a_wrong_name_is_refused():
    for mode in MODES:
        llm = MockRouterLlm()
        route = route_question("What is FiD?", INDEX, llm, force=mode)
        assert route.mode == mode and route.source == "forced" and route.confidence == 1.0
        assert llm.calls == 0 and not route.ran_as_fallback
    with pytest.raises(ValueError):
        route_question("What is FiD?", INDEX, force="teleport")


def test_a_question_with_a_secret_is_routed_without_it_reaching_the_classifier():
    seen = []

    class Spy(MockRouterLlm):
        def complete(self, system, user, max_output_tokens, json_schema=None):
            seen.append(user)
            return super().complete(system, user, max_output_tokens, json_schema)

    route_question("Hello friend sk-abcdefghijklmnopqrstuvwx and a@b.com", INDEX, Spy())
    assert seen and "sk-abcdefghijklmnop" not in seen[0] and "a@b.com" not in seen[0]
