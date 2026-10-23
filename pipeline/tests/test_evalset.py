import json

import pytest

from graphlens_pipeline.evalset import load_questions, render_review, verify

UNITS = {"u_1": "The model reaches   65.9 accuracy\non MiraQA.", "u_2": "Second unit text."}


def question(qid="L01", kind="local", quote="reaches 65.9 accuracy", unit="u_1", **overrides):
    base = {
        "id": qid, "kind": kind, "question": "What accuracy?", "reference_answer": "65.9",
        "evidence": [{"paper_id": "p", "unit_id": unit, "quote": quote}],
    }  # fmt: skip
    return {**base, **overrides}


def messages(questions, counts=None):
    return [p.message for p in verify(questions, UNITS, counts)]


def test_valid_question_has_no_problems_even_with_different_whitespace():
    assert messages([question()]) == []


def test_quote_that_is_not_in_the_text_is_reported():
    assert any("quote not found" in m for m in messages([question(quote="reaches 99 accuracy")]))


def test_missing_unit_is_reported():
    assert any("does not exist" in m for m in messages([question(unit="u_missing")]))


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("question", "  ", "question text is empty"),
        ("reference_answer", "", "reference answer is empty"),
        ("evidence", [], "no evidence"),
        ("kind", "odd", "unknown kind"),
    ],
)
def test_incomplete_questions_are_reported(field, value, expected):
    assert any(expected in m for m in messages([question(**{field: value})]))


def test_empty_quote_is_reported():
    assert any("empty quote" in m for m in messages([question(quote="  ")]))


def test_duplicate_ids_are_reported():
    assert any("more than once" in m for m in messages([question(), question()]))


def test_expected_counts_are_enforced():
    found = messages([question()], {"local": 2, "global": 1})
    assert any("expected 2 local" in m for m in found)
    assert any("expected 1 global" in m for m in found)


def test_review_page_lists_every_question_and_its_evidence():
    page = render_review([question(), question("G01", "global", unit="u_2", quote="Second unit")])
    assert "### L01" in page and "### G01" in page
    assert "reaches 65.9 accuracy" in page and "Your decision" in page


def test_load_questions_reads_the_file(tmp_path):
    path = tmp_path / "q.json"
    path.write_text(json.dumps({"questions": [question()]}), encoding="utf-8")
    assert load_questions(path)[0]["id"] == "L01"
