"""Small helpers for the Phase 7 experiments (context size, the stricter prompt, relate diagnosis).

Pure functions only: the commands that call the databases and the model live in __main__.py.
"""

from collections import Counter

RANK = {"incorrect": 0, "partial": 1, "correct": 2}


def compare_with_previous(
    rows, previous: list[dict], system: str, previous_system: str = "local"
) -> dict:
    """Question by question: is the new run better, the same or worse than the saved run?

    `rows` are the new judged rows, `previous` the saved `answers` list of an earlier evaluation
    file (dicts with id, system and verdict). Only questions found in both are compared."""
    old = {a["id"]: a["verdict"] for a in previous if a["system"] == previous_system}
    wins = ties = losses = 0
    changed = []
    for row in rows:
        if row.system != system or row.failed or row.question_id not in old:
            continue
        new, before = RANK.get(row.verdict, 0), RANK.get(old[row.question_id], 0)
        if new > before:
            wins += 1
        elif new < before:
            losses += 1
        else:
            ties += 1
        if new != before:
            changed.append((row.question_id, old[row.question_id], row.verdict))
    return {"better": wins, "same": ties, "worse": losses, "changed": changed}


def refusal_report(records: list[dict]) -> dict:
    """`records` have an id and the status the system gave (answered, refused or clarify)."""
    kept = {"refused", "clarify"}
    refused = [r["id"] for r in records if r["status"] in kept]
    answered = [r["id"] for r in records if r["status"] not in kept]
    return {
        "questions": len(records),
        "refused": len(refused),
        "accuracy": round(len(refused) / len(records), 3) if records else None,
        "answered_anyway": sorted(answered),
    }


def relate_causes(records: list[dict]) -> dict:
    """Why a relate explanation did not pass the citation check, counted by cause."""
    causes: Counter = Counter()
    for r in records:
        if r["status"] != "answered":
            causes[f"status {r['status']}"] += 1
        elif r["check"] == "verified":
            causes["verified"] += 1
        else:
            if r["unknown_labels"]:
                causes["cites a label that is not in the context"] += 1
            if r["unsupported"]:
                causes["a sentence names an entity that is not in the context"] += 1
            if not r["unknown_labels"] and not r["unsupported"]:
                causes[f"other ({r['check']})"] += 1
    return dict(causes)
