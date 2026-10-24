"""Tests for the owner's review pages. Made-up data; nothing calls a model."""

from __future__ import annotations

import json

from graphlens_pipeline.globaleval import CRITERIA
from graphlens_pipeline.reviewsheets import (
    render_community_sheet,
    render_verdict_sheet,
    sample_communities,
    sample_verdicts,
)


def community(n, level=1, stub=False):
    return {
        "id": f"c_{n:04d}", "level": level, "size": 10 + n, "is_stub": stub,
        "title": f"Title {n}", "summary": f"Summary {n}",
        "findings": json.dumps([{"summary": f"Finding {n}a"}, {"summary": f"Finding {n}b"}]),
        "members": [f"Member {n}-{i} (Method)" for i in range(3)],
    }  # fmt: skip


def judged(n):
    outcome = dict.fromkeys(CRITERIA, "ours")
    outcome["directness"] = "tie"
    return {
        "id": f"G{n:02d}", "question": f"Question {n}?", "baseline": "short answer",
        "ours": "longer answer", "outcome": outcome,
        "reasons": {name: ["first | reason", "second reason"] for name in CRITERIA},
    }  # fmt: skip


def test_the_community_sample_skips_stubs_follows_the_quota_and_is_repeatable():
    rows = [community(n, level=n % 3, stub=n % 7 == 0) for n in range(1, 120)]
    first = sample_communities(rows)
    assert first == sample_communities(list(reversed(rows)))
    assert not any(c["is_stub"] for c in first)
    per_level = {lvl: sum(1 for c in first if c["level"] == lvl) for lvl in (0, 1, 2)}
    assert per_level == {0: 5, 1: 10, 2: 5} and len({c["id"] for c in first}) == 20


def test_a_level_with_few_communities_gives_what_it_has():
    rows = [community(n, level=0) for n in range(1, 4)] + [community(10, level=1)]
    got = sample_communities(rows)
    assert len(got) == 4


def test_verdict_sample_only_takes_judged_questions_in_question_order():
    results = [judged(n) for n in range(1, 21)] + [{"id": "G99", "outcome": None}]
    picked = sample_verdicts(results, 10)
    assert len(picked) == 10 and [r["id"] for r in picked] == sorted(r["id"] for r in picked)
    assert all(r["outcome"] for r in picked)


def test_the_sheets_show_what_the_owner_needs_to_judge():
    community_sheet = render_community_sheet([community(1), community(2)])
    assert "## K01: Title 1" in community_sheet and "Member 1-0 (Method)" in community_sheet
    assert "Your rating (1 to 5)" in community_sheet and "Finding 2b" in community_sheet
    verdict_sheet = render_verdict_sheet([judged(3)])
    assert "## V01: G03 Question 3?" in verdict_sheet
    assert "| comprehensiveness | B (global) |" in verdict_sheet
    assert "| directness | tie |" in verdict_sheet
    assert "first / reason" in verdict_sheet  # a pipe in a reason cannot break the table
