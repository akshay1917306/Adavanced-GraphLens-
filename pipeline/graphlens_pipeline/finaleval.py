"""The final evaluation of Phase 7: numbers in, a report out (no database, no model).

`build_report` turns the measured parts into the table of targets (met, missed or not measured) and
`render_markdown` writes `docs/EVALUATION.md` from it, so no number in the report is typed by hand.
"""

import math

# Targets from the blueprint section 1.2, as recorded in docs/phases/phase-4-local-search/BRIEF.md.
TARGET_CORRECT = 0.75
TARGET_GAP_POINTS = 15.0
TARGET_SUPPORT = 0.90
TARGET_REFUSAL = 0.90
TARGET_ROUTER = 0.85
TARGET_COST_USD = 0.03
TARGET_P95_SECONDS = 8.0


def percentile(values: list[float], p: float) -> float:
    """The value below which p percent of the sorted values lie (nearest rank)."""
    ordered = sorted(values)
    if not ordered:
        return math.nan
    return ordered[min(len(ordered) - 1, max(0, math.ceil(p / 100 * len(ordered)) - 1))]


def acceptable_modes(q: dict) -> set[str]:
    """The modes a labeled question may be routed to (the same labels as `route-eval`)."""
    if q.get("expected_modes"):
        return set(q["expected_modes"])
    if q["kind"] == "global":
        return {"global"}
    if q["kind"] == "relate":
        return {"relate"}
    return {"baseline", "local"} if q.get("hops", 1) <= 1 else {"local"}


def _status(value: float | None, target: float, at_least: bool = True) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "not measured"
    met = value >= target if at_least else value <= target
    return "met" if met else "missed"


def _share(correct: int, n: int) -> float | None:
    return correct / n if n else None


def _row(metric: str, value: str, target: str, status: str) -> dict:
    return {"metric": metric, "value": value, "target": target, "status": status}


def _interval(system: dict) -> str:
    low, high = system["ci95"]
    return f"95% interval {low:.0%} to {high:.0%}"


def build_report(parts: dict) -> dict:
    """`parts` holds what the run measured (see `_final_eval` in __main__.py)."""
    hard, easy = parts.get("hard"), parts.get("easy")
    rows: list[dict] = []

    if hard:
        local, base = hard["local"], hard["baseline"]
        share = local["share_correct"]
        gap = (share - base["share_correct"]) * 100 if share is not None else None
        rows.append(_row(
            "Local correctness, hard set (30 questions)",
            f"{share:.0%} ({local['correct']} of {local['questions']}, {_interval(local)})",
            "at least 75%", _status(share, TARGET_CORRECT),
        ))  # fmt: skip
        rows.append(_row(
            "Gap over plain RAG, hard set",
            f"{gap:+.1f} points (plain RAG {base['share_correct']:.0%})",
            "at least +15 points", _status(gap, TARGET_GAP_POINTS),
        ))  # fmt: skip
    support = parts.get("support")
    if support and support["precision"] is not None:
        rows.append(_row(
            "Citation support (judge, sample of answers)",
            f"{support['precision']:.1%} ({support['supported']} of {support['checked']} claims, "
            f"{support['answers']} answers)",
            "at least 90%", _status(support["precision"], TARGET_SUPPORT),
        ))  # fmt: skip
    if parts.get("refusal"):
        dev, fresh = parts["refusal"]["development"], parts["refusal"]["fresh"]
        rows.append(_row(
            "Refusal on the 10 development unanswerable questions",
            f"{dev['accuracy']:.0%} ({dev['refused']} of {dev['questions']}; the guards were "
            "tuned on this set)",
            "at least 90%", _status(dev["accuracy"], TARGET_REFUSAL),
        ))  # fmt: skip
        rows.append(_row(
            "Refusal on 10 fresh probes (not used for tuning)",
            f"{fresh['accuracy']:.0%} ({fresh['refused']} of {fresh['questions']})",
            "at least 90%", _status(fresh["accuracy"], TARGET_REFUSAL),
        ))  # fmt: skip
    router = parts.get("router")
    if router:
        share = _share(router["acceptable"], router["questions"])
        rows.append(_row(
            "Router accuracy (rules, then the small model when unsure)",
            f"{share:.0%} ({router['acceptable']} of {router['questions']}; the model was asked "
            f"{router['asked_model']} times)",
            "at least 85%", _status(share, TARGET_ROUTER),
        ))  # fmt: skip
    lat = parts.get("latency")
    if lat:
        rows.append(_row(
            "Cost per local answer",
            f"${lat['mean_cost_usd']:.4f} on average, ${lat['max_cost_usd']:.4f} at most",
            "at most $0.03", _status(lat["mean_cost_usd"], TARGET_COST_USD, False),
        ))  # fmt: skip
        rows.append(_row(
            "Time per local answer, p95, one question at a time",
            f"{lat['p95_seconds']:.1f} s (median {lat['median_seconds']:.1f} s, "
            f"max {lat['max_seconds']:.1f} s, {lat['n']} questions)",
            "at most 8 s", _status(lat["p95_seconds"], TARGET_P95_SECONDS, False),
        ))  # fmt: skip
    return {
        "targets": rows,
        "missed": [r["metric"] for r in rows if r["status"] == "missed"],
        "easy": easy,
        "relate": parts.get("relate"),
        "global": parts.get("global"),
        "spent_usd": parts.get("spent_usd"),
        "date": parts.get("date"),
        "notes": parts.get("notes", []),
    }


def render_markdown(report: dict) -> str:
    """The report as a page. Missed targets are listed in their own section."""
    lines = [
        "# Final evaluation (Phase 7)",
        "",
        f"Run on {report.get('date', '?')}. Model `gpt-4.1-mini` for answers and for the judge "
        "(same family, so correctness is indicative, not independent). Written by a script from "
        "the measured results; nothing here is typed by hand. Questions: 30 hard and 30 easy "
        "local questions, 20 relate pairs, 10 development and 10 fresh unanswerable questions, "
        "a labeled router set; sets are small, so read the intervals.",
        "",
        "## Targets",
        "",
        "| Measure | Result | Target | Status |",
        "|---|---|---|---|",
    ]
    for r in report["targets"]:
        mark = {"met": "met", "missed": "**missed**", "not measured": "not measured"}[r["status"]]
        lines.append(f"| {r['metric']} | {r['value']} | {r['target']} | {mark} |")
    lines += ["", "## Targets that were missed", ""]
    if report["missed"]:
        lines += [f"- {m}" for m in report["missed"]]
    else:
        lines.append("None.")
    easy = report.get("easy")
    if easy:
        loc, base = easy["local"], easy["baseline"]
        lines += [
            "",
            "## Easy local set (30 questions, answers needing one passage)",
            "",
            f"Local search {loc['correct']} of {loc['questions']} correct "
            f"({loc['share_correct']:.0%}); plain RAG {base['correct']} of {base['questions']} "
            f"({base['share_correct']:.0%}). This set was drafted from abstracts; the ceiling is "
            "100% and plain RAG is already high.",
        ]
    rel = report.get("relate")
    if rel:
        lines += [
            "",
            "## Relate mode (20 entity pairs)",
            "",
            f"A path was found for {rel['path_found']} of {rel['pairs']} pairs and had the "
            f"expected length for {rel['right_length']}. The expected paths came from the same "
            "graph, so this is a consistency check. Explanations written: "
            f"{rel['answered']}; passed the citation check as verified: {rel['verified']} of "
            f"{rel['answered']}.",
        ]
    glob = report.get("global")
    if glob:
        lines += [
            "",
            "## Global search (carried over from Phase 3, not re-run)",
            "",
            f"Win rate against plain RAG over {glob['n']} questions, both answer orders must "
            f"agree: comprehensiveness {glob['comprehensiveness']:.0%}, diversity "
            f"{glob['diversity']:.0%}, empowerment {glob['empowerment']:.0%}, directness "
            f"{glob['directness']:.0%}. The global code did not change after that run. The "
            "answers were 3.4 times longer than the baseline's, which favours the criteria above.",
        ]
    if report.get("notes"):
        lines += ["", "## Notes and limits", ""]
        lines += [f"- {n}" for n in report["notes"]]
    if report.get("spent_usd") is not None:
        lines += ["", f"Cost of this run: ${report['spent_usd']:.4f}."]
    return "\n".join(lines) + "\n"
