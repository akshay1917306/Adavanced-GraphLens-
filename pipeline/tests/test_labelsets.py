"""Tests for the labeled-set helpers. All data is made up; nothing calls a model."""

from __future__ import annotations

import pytest

from graphlens_pipeline.extract import Entity, Relation, UnitResult
from graphlens_pipeline.labelsets import (
    _stratum,
    draw,
    draw_units,
    er_scores,
    final_label,
    relation_items,
    relation_precision,
    render_pair_review,
    render_relation_review,
    validate,
)


def result(uid, n_relations):
    return UnitResult(
        uid,
        [Entity("A", "Method", "d"), Entity("B", "Dataset", "d")],
        [Relation("A", "EVALUATED_ON", "B", "d", 5) for _ in range(n_relations)],
    )


def unit(uid):
    return {"id": uid, "title": "Paper", "section": "Intro", "text": "text " + uid}


def test_the_draw_is_the_same_every_time_and_ignores_input_order():
    items = [f"u{i}" for i in range(50)]
    first = draw(items, lambda x: x, 10)
    assert first == draw(list(reversed(items)), lambda x: x, 10) and len(first) == 10


def test_units_with_fewer_than_two_relations_are_not_drawn():
    units = [unit("a"), unit("b"), unit("c")]
    results = {"a": result("a", 1), "b": result("b", 3), "c": result("c", 2)}
    assert {u["id"] for u in draw_units(units, results, 10)} == {"b", "c"}


def test_relation_items_get_unique_ids_and_empty_labels():
    data = relation_items([unit("a"), unit("b")], {"a": result("a", 2), "b": result("b", 1)})
    ids = [r["id"] for u in data["units"] for r in u["relations"]]
    assert ids == ["R01.1", "R01.2", "R02.1"]
    assert all(
        r["draft"] is None and r["owner"] is None for u in data["units"] for r in u["relations"]
    )


@pytest.mark.parametrize(
    ("method", "decision", "rationale", "expected"),
    [
        ("auto_merge", "merge", "", "auto_merge"),
        ("llm", "merge", "same", "llm_merge"),
        ("llm", "keep_separate", "names differ (model said: same)", "guard_veto"),
        ("llm", "keep_separate", "broader", "llm_keep"),
        ("rejected", "keep_separate", "different numbers", "rule_blocked"),
    ],
)
def test_decisions_fall_into_strata(method, decision, rationale, expected):
    assert _stratum(method, decision, rationale) == expected


def test_the_owner_label_wins_over_the_draft():
    assert final_label({"draft": "correct", "owner": "incorrect"}) == ("incorrect", "owner")
    assert final_label({"draft": "correct", "owner": None}) == ("correct", "draft")
    assert final_label({"draft": None, "owner": None}) == (None, "none")


def data_with(labels):
    return {
        "units": [{"relations": [{"draft": lab, "owner": None} for lab in labels]}],
    }


def test_relation_precision_ignores_unsure_and_counts_unlabeled():
    score = relation_precision(data_with(["correct", "correct", "incorrect", "unsure", None]))
    assert score.value == pytest.approx(2 / 3)
    assert (score.counted, score.unsure, score.unlabeled, score.draft_only) == (3, 1, 1, 4)


def pair(decision, label, weight=1.0):
    return {"decision": decision, "draft": label, "owner": None, "weight": weight}


def test_er_scores_use_the_weights_of_each_stratum():
    pairs = [
        pair("merge", "same", 10), pair("merge", "different", 10),  # precision 0.5
        pair("keep_separate", "same", 5),  # one missed merge, worth 5
        pair("keep_separate", "different", 50),
    ]  # fmt: skip
    scores = er_scores({"pairs": pairs})
    assert scores["precision"].value == pytest.approx(0.5)
    assert scores["recall"].value == pytest.approx(10 / 15)
    assert scores["f1"].value == pytest.approx(2 * 0.5 * (10 / 15) / (0.5 + 10 / 15))


def test_er_scores_are_none_without_labels():
    assert er_scores({"pairs": [pair("merge", None)]})["f1"].value is None


def test_bad_label_values_are_reported():
    relations = {"units": [{"relations": [{"id": "R1", "draft": "maybe", "owner": None}]}]}
    pairs = {"pairs": [{"id": "P1", "draft": "same", "owner": "sort of"}]}
    problems = validate(relations, pairs)
    assert len(problems) == 2 and "R1" in problems[0] and "P1" in problems[1]


def test_the_review_pages_show_text_labels_and_ids():
    relations = relation_items([unit("a")], {"a": result("a", 1)})
    page = render_relation_review(relations)
    assert "R01.1" in page and "text a" in page and "EVALUATED_ON" in page
    pairs = {"pairs": [{
        "id": "P001", "a": "Method:DPR", "b": "Method:Dense Passage Retrieval",
        "a_description": "", "b_description": "", "decision": "merge", "draft": "same",
        "owner": None, "reason": "acronym",
    }]}  # fmt: skip
    assert "P001" in render_pair_review(pairs) and "acronym" in render_pair_review(pairs)
