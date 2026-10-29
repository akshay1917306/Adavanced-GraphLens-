"""The final evaluation report: targets, statuses and the page. No database, no model."""

import math

import pytest

from graphlens_pipeline.finaleval import (
    acceptable_modes,
    build_report,
    percentile,
    render_markdown,
)


def system(correct, n=30):
    low = (correct - 3) / n
    return {"questions": n, "correct": correct, "share_correct": correct / n,
            "ci95": [max(0, low), min(1, correct / n + 0.1)]}  # fmt: skip


def parts(**over):
    base = {
        "hard": {"local": system(21), "baseline": system(16)},
        "easy": {"local": system(29), "baseline": system(28)},
        "support": {"checked": 124, "supported": 122, "answers": 20, "precision": 122 / 124},
        "refusal": {
            "development": {"questions": 10, "refused": 10, "accuracy": 1.0, "answered_anyway": []},
            "fresh": {"questions": 10, "refused": 9, "accuracy": 0.9, "answered_anyway": ["F03"]},
        },
        "router": {"questions": 100, "acceptable": 90, "asked_model": 12},
        "latency": {
            "n": 60,
            "median_seconds": 5.2,
            "p95_seconds": 9.1,
            "max_seconds": 12.0,
            "mean_cost_usd": 0.0035,
            "max_cost_usd": 0.0051,
        },  # fmt: skip
        "relate": {
            "pairs": 20,
            "path_found": 20,
            "right_length": 20,
            "answered": 20,
            "verified": 17,
        },
        "global": {
            "n": 20,
            "comprehensiveness": 1.0,
            "diversity": 1.0,
            "empowerment": 1.0,
            "directness": 0.45,
        },  # fmt: skip
        "spent_usd": 0.41,
        "date": "2026-10-30",
        "notes": ["A note."],
    }
    base.update(over)
    return base


def status_of(report, fragment):
    return next(r["status"] for r in report["targets"] if fragment in r["metric"])


def test_percentile_uses_the_nearest_rank_and_survives_an_empty_list():
    values = list(range(1, 101))
    assert percentile(values, 95) == 95 and percentile(values, 50) == 50
    assert percentile([3.0], 95) == 3.0
    assert math.isnan(percentile([], 95))


def test_each_target_is_met_or_missed_by_its_own_number():
    report = build_report(parts())
    assert status_of(report, "Local correctness") == "missed"  # 70% against 75%
    assert status_of(report, "Gap over plain RAG") == "met"  # +16.7 points against 15
    assert status_of(report, "Citation support") == "met"
    assert status_of(report, "development unanswerable") == "met"
    assert status_of(report, "fresh probes") == "met"
    assert status_of(report, "Router") == "met"
    assert status_of(report, "Cost per local answer") == "met"
    assert status_of(report, "p95") == "missed"  # 9.1 s against 8 s
    assert report["missed"] == [
        "Local correctness, hard set (30 questions)",
        "Time per local answer, p95, one question at a time",
    ]


def test_a_target_exactly_on_the_line_is_met_and_a_missing_measurement_is_not_measured():
    exact = parts(hard={"local": system(24, 32), "baseline": system(10, 32)})
    exact["hard"]["local"]["share_correct"] = 0.75
    assert status_of(build_report(exact), "Local correctness") == "met"
    no_latency = parts()
    del no_latency["latency"]
    report = build_report(no_latency)
    assert all("p95" not in r["metric"] for r in report["targets"])


def test_the_page_lists_missed_targets_and_carries_the_caveats():
    page = render_markdown(build_report(parts()))
    assert "## Targets that were missed" in page
    assert "- Local correctness, hard set (30 questions)" in page
    assert "**missed**" in page and "| met |" in page
    assert "carried over from Phase 3, not re-run" in page
    assert "17 of 20" in page and "A note." in page and "$0.4100" in page
    assert "tuned on this set" in page  # the development refusal number says so itself


def test_with_nothing_missed_the_page_says_so():
    good = parts(hard={"local": system(27), "baseline": system(15)})
    good["latency"]["p95_seconds"] = 7.0
    page = render_markdown(build_report(good))
    assert "## Targets that were missed\n\nNone." in page


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ({"kind": "global"}, {"global"}),
        ({"kind": "relate"}, {"relate"}),
        ({"kind": "local", "hops": 1}, {"baseline", "local"}),
        ({"kind": "local", "hops": 2}, {"local"}),
        ({"kind": "local", "hops": 1, "expected_modes": ["relate"]}, {"relate"}),
    ],
)
def test_the_acceptable_modes_follow_the_labels(question, expected):
    assert acceptable_modes(question) == expected
