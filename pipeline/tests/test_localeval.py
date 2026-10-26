"""Tests for the small paid evaluation. The answerers and the judge are labelled MOCKs; the cache
is the real Postgres table; nothing calls OpenAI."""

from __future__ import annotations

import json

import pytest

from graphlens_pipeline.llm import LlmError, LlmResult
from graphlens_pipeline.localeval import (
    AnswerRecord,
    Row,
    check_support,
    paired,
    refusal_accuracy,
    run_correctness,
    summarize,
    support_sample,
)


class MockJudgeLlm:
    """MOCK model for both judges: the correctness verdict depends on a marker in the answer,
    the support check returns fixed numbers."""

    model = "gpt-4.1-mini"

    def __init__(self, error=None):
        self.calls, self.error = 0, error

    def complete(self, system, user, max_output_tokens, json_schema=None):
        self.calls += 1
        if self.error:
            raise self.error
        if json_schema is not None:  # the support check
            return LlmResult(json.dumps({"checked": 4, "supported": 3}), self.model, 900, 20)
        verdict = "correct" if "RIGHT" in user.split("<candidate_answer>")[1] else "incorrect"
        return LlmResult(json.dumps({"verdict": verdict, "reason": "mock"}), self.model, 400, 30)


def questions(n):
    return [
        {"id": f"M{i:02d}", "question": f"Question {i}?", "reference_answer": "ref"}
        for i in range(1, n + 1)
    ]


def answer_fn(right_ids=(), status="answered", cost=0.004):
    def run(question):
        number = int(question.split()[1].rstrip("?"))
        text = ("RIGHT " if number in right_ids else "WRONG ") + question
        passages = {"T1": "passage text"} if status == "answered" else {}
        return AnswerRecord("x", text, status, cost, 1.5, "verified", ["T1"], passages)

    return run


@pytest.fixture
def empty_cache(engine):
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE extraction_cache"))


@pytest.mark.integration
def test_answers_are_judged_summarised_and_compared_pairwise(engine, empty_cache):
    llm = MockJudgeLlm()
    fns = {"baseline": answer_fn(right_ids=(1,)), "local": answer_fn(right_ids=(1, 2, 3))}
    rows, cost, skipped = run_correctness(engine, llm, questions(4), fns, max_cost_usd=1.0)
    summary = summarize(rows)
    assert summary["baseline"]["correct"] == 1 and summary["local"]["correct"] == 3
    assert summary["local"]["share_correct"] == 0.75 and summary["local"]["citation_checks"] == {
        "verified": 4
    }
    assert paired(rows, "local", "baseline") == {"wins": 2, "ties": 2, "losses": 0}
    # 8 answers; an identical answer from both systems is judged once (twice if two workers
    # reach it at the same moment), so the number of judge calls is 6 to 8
    assert cost > 0 and skipped == 0 and 6 <= llm.calls <= 8


@pytest.mark.integration
def test_a_repeat_costs_nothing_because_answers_and_verdicts_are_cached(engine, empty_cache):
    fns = {"local": answer_fn(right_ids=(1,))}
    run_correctness(engine, MockJudgeLlm(), questions(3), fns, max_cost_usd=1.0)
    llm = MockJudgeLlm()
    calls = []

    def must_not_run(question):
        calls.append(question)
        return AnswerRecord("local")

    rows, cost, _ = run_correctness(engine, llm, questions(3), {"local": must_not_run}, 1.0)
    assert llm.calls == 0 and calls == [] and cost == 0
    assert summarize(rows)["local"]["correct"] == 1


@pytest.mark.integration
def test_the_cost_cap_stops_new_work_and_a_refusal_counts_as_a_miss(engine, empty_cache):
    rows, cost, skipped = run_correctness(
        engine, MockJudgeLlm(), questions(5), {"local": answer_fn(cost=0.6)}, max_cost_usd=1.0,
        workers=1,
    )  # fmt: skip
    assert skipped >= 1 and len(rows) < 5
    fresh = [{"id": "X1", "question": "Question 9?", "reference_answer": "ref"},
             {"id": "X2", "question": "Question 8?", "reference_answer": "ref"}]  # fmt: skip
    refused, _, _ = run_correctness(
        engine, MockJudgeLlm(), fresh, {"local": answer_fn(status="refused")}, 1.0
    )
    summary = summarize(refused)["local"]
    assert {r.verdict for r in refused} == {"incorrect"} and summary["refused"] == 2


@pytest.mark.integration
def test_a_failing_judge_is_reported_not_hidden(engine, empty_cache):
    rows, _, _ = run_correctness(
        engine, MockJudgeLlm(error=LlmError("model call failed (APIConnectionError)")),
        questions(2), {"local": answer_fn()}, 1.0,
    )  # fmt: skip
    assert all(r.failed for r in rows) and summarize(rows)["local"]["questions"] == 0


@pytest.mark.integration
def test_the_support_check_is_cached_and_clamped(engine, empty_cache):
    row = Row("M01", "q", "local", AnswerRecord("local", "A claim [T1].", passages={"T1": "p"}))
    llm = MockJudgeLlm()
    assert check_support(engine, llm, row)[:2] == (4, 3) and llm.calls == 1
    assert check_support(engine, llm, row) == (4, 3, 0.0) and llm.calls == 1  # cached


def test_the_support_sample_is_repeatable_and_needs_passages():
    rows = [
        Row(f"M{i:02d}", "q", "local", AnswerRecord("local", "t", passages={"T1": "p"}))
        for i in range(1, 31)
    ] + [Row("M99", "q", "local", AnswerRecord("local", "t"))]
    first = support_sample(rows, "local", 20)
    assert [r.question_id for r in first] == [
        r.question_id for r in support_sample(rows[::-1], "local", 20)
    ]
    assert len(first) == 20 and "M99" not in {r.question_id for r in first}


def test_refusal_accuracy_names_the_questions_that_were_answered_anyway():
    got = refusal_accuracy(
        {"U01": "refused", "U02": "clarify", "U03": "answered", "U04": "no_report"}
    )
    assert got["accuracy"] == 0.75 and got["answered_anyway"] == ["U03"]
    assert refusal_accuracy({})["accuracy"] is None
