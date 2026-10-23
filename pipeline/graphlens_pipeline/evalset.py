"""The evaluation set: questions with reference answers and exact evidence quotes.

Every question points at text units and quotes a short exact phrase from each. `verify`
checks that the unit exists and that the quote really appears in its text, so the answer
key cannot contain a fact that the corpus does not contain.
"""

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, text

KINDS = {"local", "global"}


@dataclass(frozen=True)
class Problem:
    question_id: str
    message: str


def load_questions(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["questions"]


def _squash(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def verify(
    questions: list[dict],
    unit_texts: dict[str, str],
    expected_counts: dict[str, int] | None = None,
) -> list[Problem]:
    """Return every problem found. An empty list means the set is consistent."""
    problems: list[Problem] = []
    ids = Counter(q.get("id", "?") for q in questions)
    for question_id, count in ids.items():
        if count > 1:
            problems.append(Problem(question_id, "id used more than once"))

    for question in questions:
        qid = question.get("id", "?")
        if question.get("kind") not in KINDS:
            problems.append(Problem(qid, f"unknown kind {question.get('kind')!r}"))
        if not _squash(question.get("question", "")):
            problems.append(Problem(qid, "question text is empty"))
        if not _squash(question.get("reference_answer", "")):
            problems.append(Problem(qid, "reference answer is empty"))
        evidence = question.get("evidence") or []
        if not evidence:
            problems.append(Problem(qid, "no evidence"))
        for item in evidence:
            unit_text = unit_texts.get(item.get("unit_id", ""))
            if unit_text is None:
                problems.append(Problem(qid, f"unit {item.get('unit_id')} does not exist"))
            elif not _squash(item.get("quote", "")):
                problems.append(Problem(qid, f"empty quote for {item['unit_id']}"))
            elif _squash(item["quote"]) not in _squash(unit_text):
                problems.append(Problem(qid, f"quote not found in {item['unit_id']}"))

    if expected_counts:
        found = Counter(q.get("kind") for q in questions)
        for kind, wanted in expected_counts.items():
            if found.get(kind, 0) != wanted:
                problems.append(
                    Problem("-", f"expected {wanted} {kind} questions, found {found.get(kind, 0)}")
                )
    return problems


def fetch_unit_texts(engine: Engine, unit_ids: set[str]) -> dict[str, str]:
    if not unit_ids:
        return {}
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, text FROM text_units WHERE id = ANY(:ids)"), {"ids": sorted(unit_ids)}
        ).all()
    return {row.id: row.text for row in rows}


def render_review(questions: list[dict]) -> str:
    """A readable page for the owner to review: question, reference answer, evidence."""
    lines = [
        "# Evaluation set v0: review page",
        "",
        "Questions were drafted by Claude from the abstracts of the 25 papers. You are the judge.",
        "For each question, check three things: (1) the question is clear, (2) the reference",
        "answer is correct for what the quoted evidence says, (3) it is not too easy or odd.",
        "Write your decision in the **Your decision** line (OK, CHANGE: ..., or DROP).",
        "",
    ]
    for kind, title in (("local", "Local questions (30)"), ("global", "Global questions (10)")):
        lines += [f"## {title}", ""]
        for q in (x for x in questions if x["kind"] == kind):
            lines += [
                f"### {q['id']}: {q['question']}",
                "",
                f"- **Reference answer:** {q['reference_answer']}",
            ]
            for item in q["evidence"]:
                lines.append(
                    f'- **Evidence** ({item["paper_id"]}, `{item["unit_id"]}`): "{item["quote"]}"'
                )
            lines += ["- **Your decision:** ", ""]
    return "\n".join(lines)
