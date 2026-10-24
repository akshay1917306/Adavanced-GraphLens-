"""Review pages for the owner at the end of Phase 3: community coherence and judge verdicts.

Both samples are drawn the same way every time (hash order), so the owner can come back to the
same items. Nothing here calls a model.
"""

from __future__ import annotations

import json

from graphlens_pipeline.globaleval import CRITERIA
from graphlens_pipeline.labelsets import draw

QUOTA = {0: 5, 1: 10, 2: 5}  # communities per level; short levels give what they have


def sample_communities(rows: list[dict], quota: dict[int, int] | None = None) -> list[dict]:
    """Model-written reports only (stubs have nothing to rate), spread over the levels."""
    quota = quota or QUOTA
    chosen = []
    for level, wanted in sorted(quota.items()):
        pool = [r for r in rows if r["level"] == level and not r["is_stub"]]
        chosen += draw(pool, lambda r: r["id"], wanted)
    return chosen


def sample_verdicts(results: list[dict], n: int = 10) -> list[dict]:
    """Questions whose answers were both judged, in a repeatable order."""
    judged = [r for r in results if r.get("outcome")]
    return sorted(draw(judged, lambda r: r["id"], n), key=lambda r: r["id"])


def render_community_sheet(items: list[dict]) -> str:
    lines = [
        "# Community review: coherence",
        "",
        "For each community below, read the title, the summary and the member list, then give a",
        "**coherence rating from 1 to 5**: 5 = the members clearly belong together and the",
        "title and summary describe them well; 3 = partly; 1 = the members are unrelated or the",
        "report does",
        "not match them. Reply with the ratings, for example `K01 4, K02 5, K03 2`. Short comments",
        "on low ratings help. (Proposed bar: an average of at least 3.5.)",
        "",
    ]
    for number, item in enumerate(items, start=1):
        findings = json.loads(item["findings"] or "[]")
        lines += [
            f"## K{number:02d}: {item['title']}",
            "",
            f"- Level {item['level']}, {item['size']} entities, community `{item['id']}`",
            f"- **Summary:** {item['summary']}",
            "- **Members (most connected first):** " + "; ".join(item["members"]),
            "- **Findings:**",
        ]
        lines += [f"  - {f['summary']}" for f in findings[:4]]
        lines += ["- **Your rating (1 to 5):** ", ""]
    return "\n".join(lines) + "\n"


def render_verdict_sheet(items: list[dict]) -> str:
    lines = [
        "# Judge review: do you agree with the verdicts?",
        "",
        "Answer A is the **plain-RAG baseline**, answer B is **global search** (the judge saw them",
        "in both orders and did not know which was which). For each question, read both",
        "answers and the verdicts. Reply per question with `agree`, or the criterion you",
        "disagree with and why,",
        "for example `V03 agree, V04 diversity: baseline is better`.",
        "The judge is the same model family as the answerer; your check is the independent one.",
        "",
    ]
    for number, item in enumerate(items, start=1):
        lines += [
            f"## V{number:02d}: {item['id']} {item['question']}",
            "",
            "### Answer A (baseline)",
            "",
            item["baseline"].strip(),
            "",
            "### Answer B (global search)",
            "",
            item["ours"].strip(),
            "",
            "### Verdicts (after both orders)",
            "",
            "| Criterion | Winner | Judge's reasons (order 1; order 2) |",
            "|---|---|---|",
        ]
        for name in CRITERIA:
            winner = {"ours": "B (global)", "baseline": "A (baseline)", "tie": "tie"}[
                item["outcome"][name]
            ]
            reasons = " ; ".join(r.replace("|", "/") for r in item["reasons"][name])
            lines.append(f"| {name} | {winner} | {reasons} |")
        lines += ["", "**Your decision:** ", ""]
    return "\n".join(lines) + "\n"
