"""Labeled sets for measuring the graph: relation precision and entity-resolution scores.

How it works: this module draws the samples (seeded, so the same draw every time) and writes
them to JSON. Someone other than the extraction model drafts a label for each item, and the
owner reviews. Scores use the owner's label where there is one and say how many items are still
draft-only. Nothing here calls a model.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, text

from graphlens_pipeline.extract import UnitResult

SEED = "labels-v0"
N_UNITS = 30
# stratum -> how many pairs to draw; the strata are the kinds of decision the resolver made
PAIR_SAMPLE = {
    "auto_merge": 20,
    "llm_merge": 30,
    "guard_veto": 30,
    "llm_keep": 20,
    "rule_blocked": 10,
}
RELATION_LABELS = {"correct", "incorrect", "unsure"}
PAIR_LABELS = {"same", "different", "unsure"}


def _order(key: str) -> str:
    return hashlib.sha256(f"{SEED}|{key}".encode()).hexdigest()


def draw(items: list, key, n: int) -> list:
    """The same `n` items every time, spread by hash rather than by position."""
    return sorted(items, key=lambda item: _order(key(item)))[:n]


def draw_units(units: list[dict], results: dict[str, UnitResult], n: int = N_UNITS) -> list[dict]:
    """Units that have at least two relations (otherwise there is little to judge)."""
    usable = [u for u in units if len(results[u["id"]].relations) >= 2]
    return draw(usable, lambda u: u["id"], n)


def relation_items(units: list[dict], results: dict[str, UnitResult]) -> dict:
    out = []
    for unit in units:
        relations = [
            {
                "id": f"R{len(out) + 1:02d}.{i + 1}",
                "source": r.source, "predicate": r.predicate, "target": r.target,
                "description": r.description, "draft": None, "reason": None, "owner": None,
            }
            for i, r in enumerate(results[unit["id"]].relations)
        ]  # fmt: skip
        out.append(
            {
                "unit_id": unit["id"],
                "paper": unit["title"],
                "section": unit["section"],
                "text": unit["text"],
                "relations": relations,
            }
        )
    return {"version": 0, "seed": SEED, "units": out}


def _stratum(method: str, decision: str, rationale: str) -> str:
    if method == "auto_merge":
        return "auto_merge"
    if method == "llm" and decision == "merge":
        return "llm_merge"
    if method == "llm" and "model said" in (rationale or ""):
        return "guard_veto"
    if method == "llm":
        return "llm_keep"
    return "rule_blocked"


def pair_items(engine: Engine, run_id: str, results: dict[str, UnitResult]) -> dict:
    """A stratified sample of the resolver's decisions, each with a weight so scores can be
    scaled back up to all decisions."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT entity_a, entity_b, score, method, decision, rationale"
                " FROM resolution_decisions WHERE run_id = :r"
            ),
            {"r": run_id},
        ).all()
    described: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for result in results.values():
        for entity in result.entities:
            described[(entity.type, entity.name)][entity.description] += 1

    def describe(label: str) -> str:
        type_, _, name = label.partition(":")
        counter = described.get((type_, name))
        return counter.most_common(1)[0][0][:200] if counter else ""

    strata: dict[str, list] = defaultdict(list)
    for a, b, score, method, decision, rationale in rows:
        strata[_stratum(method, decision, rationale)].append((a, b, score, decision, rationale))
    pairs = []
    for name, wanted in PAIR_SAMPLE.items():
        members = strata.get(name, [])
        chosen = draw(members, lambda m: f"{m[0]}|{m[1]}", wanted)
        for a, b, score, decision, rationale in chosen:
            pairs.append(
                {
                    "id": f"P{len(pairs) + 1:03d}", "stratum": name,
                    "weight": len(members) / len(chosen), "a": a, "b": b,
                    "a_description": describe(a), "b_description": describe(b),
                    "score": round(float(score or 0), 3), "decision": decision,
                    "rationale": rationale or "", "draft": None, "reason": None, "owner": None,
                }
            )  # fmt: skip
    return {
        "version": 0, "seed": SEED, "run_id": run_id,
        "stratum_sizes": {k: len(v) for k, v in strata.items()}, "pairs": pairs,
    }  # fmt: skip


def final_label(item: dict) -> tuple[str | None, str]:
    """(label, source) where source is owner, draft or none."""
    if item.get("owner"):
        return item["owner"], "owner"
    if item.get("draft"):
        return item["draft"], "draft"
    return None, "none"


@dataclass
class Score:
    value: float | None
    counted: int
    unsure: int
    owner_reviewed: int
    draft_only: int
    unlabeled: int
    details: dict


def relation_precision(data: dict) -> Score:
    labels = [final_label(r) for unit in data["units"] for r in unit["relations"]]
    right = sum(1 for lab, _ in labels if lab == "correct")
    wrong = sum(1 for lab, _ in labels if lab == "incorrect")
    return Score(
        value=right / (right + wrong) if right + wrong else None,
        counted=right + wrong,
        unsure=sum(1 for lab, _ in labels if lab == "unsure"),
        owner_reviewed=sum(1 for _, s in labels if s == "owner"),
        draft_only=sum(1 for _, s in labels if s == "draft"),
        unlabeled=sum(1 for _, s in labels if s == "none"),
        details={"correct": right, "incorrect": wrong, "units": len(data["units"])},
    )


def er_scores(data: dict) -> dict[str, Score]:
    """Weighted precision, recall and F1 of the merge decisions.

    A pair counts as a merge when the resolver merged it. Recall only covers pairs the resolver
    looked at (the candidates); two names that never became a pair are not seen here.
    """
    tp = fp = fn = 0.0
    labels = []
    for pair in data["pairs"]:
        label, source = final_label(pair)
        labels.append((label, source))
        merged = pair["decision"] == "merge"
        weight = pair["weight"]
        if label == "same" and merged:
            tp += weight
        elif label == "different" and merged:
            fp += weight
        elif label == "same" and not merged:
            fn += weight
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    common = dict(
        counted=sum(1 for lab, _ in labels if lab in ("same", "different")),
        unsure=sum(1 for lab, _ in labels if lab == "unsure"),
        owner_reviewed=sum(1 for _, s in labels if s == "owner"),
        draft_only=sum(1 for _, s in labels if s == "draft"),
        unlabeled=sum(1 for _, s in labels if s == "none"),
        details={"weighted_tp": round(tp, 1), "weighted_fp": round(fp, 1),
                 "weighted_fn": round(fn, 1), "stratum_sizes": data.get("stratum_sizes", {})},
    )  # fmt: skip
    return {
        "precision": Score(precision, **common),
        "recall": Score(recall, **common),
        "f1": Score(f1, **common),
    }


def render_relation_review(data: dict) -> str:
    lines = [
        "# Relation labels: review",
        "",
        "For each text unit, check every extracted relation against the passage.",
        "`draft` is Claude's first label. Reply with the IDs you disagree with and the right",
        "label (`correct`, `incorrect`, `unsure`). A relation is **correct** only if the",
        "passage supports it, the direction is right and both names are the right things.",
        "",
    ]
    for unit in data["units"]:
        lines += [
            f"## {unit['unit_id']}: {unit['paper']} ({unit['section'] or 'no section'})",
            "",
            "> " + unit["text"].replace("\n", "\n> "),
            "",
            "| ID | Relation | Draft | Why |",
            "|---|---|---|---|",
        ]
        for r in unit["relations"]:
            label = r["owner"] or r["draft"] or "?"
            lines.append(
                f"| {r['id']} | {r['source']} **{r['predicate']}** {r['target']} | {label} |"
                f" {r['reason'] or ''} |"
            )
        lines.append("")
    return "\n".join(lines)


def render_pair_review(data: dict) -> str:
    lines = [
        "# Entity pairs: review",
        "",
        "Are the two names the same real thing? Answer `same`, `different` or `unsure`.",
        "`Resolver` is what the pipeline did (merged or kept separate). `draft` is Claude's label.",
        "Reply with the IDs you disagree with and the right label.",
        "",
        "| ID | A | B | Resolver | Draft | Why |",
        "|---|---|---|---|---|---|",
    ]
    for p in data["pairs"]:
        label = p["owner"] or p["draft"] or "?"
        lines.append(
            f"| {p['id']} | {p['a']} ({p['a_description'][:70]}) |"
            f" {p['b']} ({p['b_description'][:70]}) | {p['decision']} | {label} |"
            f" {p['reason'] or ''} |"
        )
    return "\n".join(lines) + "\n"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def validate(relations: dict, pairs: dict) -> list[str]:
    """Problems with label values, for the owner's replies and my own drafts."""
    problems = []
    for unit in relations["units"]:
        for r in unit["relations"]:
            for key in ("draft", "owner"):
                if r[key] is not None and r[key] not in RELATION_LABELS:
                    problems.append(f"{r['id']}: bad {key} label {r[key]!r}")
    for p in pairs["pairs"]:
        for key in ("draft", "owner"):
            if p[key] is not None and p[key] not in PAIR_LABELS:
                problems.append(f"{p['id']}: bad {key} label {p[key]!r}")
    return problems
