import json

import pytest

from graphlens_pipeline.evalset import load_questions, remap_evidence, render_review, verify

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


def test_remap_points_evidence_at_the_unit_that_holds_the_quote():
    old = question(unit="u_old")
    units = {"p": {"u_new_0001": "text with reaches 65.9 accuracy inside", "u_new_0002": "other"}}
    remapped, problems = remap_evidence([old], units)
    assert problems == []
    assert remapped[0]["evidence"][0]["unit_id"] == "u_new_0001"
    assert old["evidence"][0]["unit_id"] == "u_old"  # the input is not changed


def test_remap_uses_the_first_unit_when_neighbours_overlap():
    units = {"p": {"u_2": "also reaches 65.9 accuracy", "u_1": "reaches 65.9 accuracy"}}
    remapped, problems = remap_evidence([question()], units)
    assert problems == [] and remapped[0]["evidence"][0]["unit_id"] == "u_1"


def test_remap_reports_a_quote_that_is_nowhere():
    units = {"p": {"u_1": "reaches 65.9 accuracy"}}
    _, problems = remap_evidence([question(quote="never appears")], units)
    assert any("not found in any unit" in p.message for p in problems)
    _, problems = remap_evidence([question()], {})
    assert any("not found in any unit" in p.message for p in problems)


def test_load_questions_reads_the_file(tmp_path):
    path = tmp_path / "q.json"
    path.write_text(json.dumps({"questions": [question()]}), encoding="utf-8")
    assert load_questions(path)[0]["id"] == "L01"
