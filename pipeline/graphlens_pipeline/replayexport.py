"""Turn saved Phase 4 answers into replay entries for the UI (no model call, no cost).

The answer texts come from a finished evaluation run. The passages and the small evidence graph
are rebuilt for the same question from the databases (local models only). An entry is kept only
when the rebuilt context still holds every cited label and the citation check gives the same
result as in the saved run; otherwise it is reported and left out, never patched.
"""

import re

from graphlens_pipeline.localanswer import check_citations, prepare_local
from graphlens_pipeline.localgraph import Subgraph

KIND_OF_LABEL = {"T": "text_unit", "E": "entity", "C": "community"}
MAX_NODES = 6
LABEL = re.compile(r"[TEC]\d+")


def _title(text: str) -> str:
    return text.strip().split("\n")[0][:80]


def pick_graph(graph: Subgraph, entity_ids: list[str]) -> tuple[list[dict], list[dict]]:
    """At most six dots: the seeds and cited entities first, then the best-scored neighbours
    that touch a chosen dot. Links are the graph edges between chosen dots."""
    by_id = {n.id: n for n in graph.nodes}
    chosen = [n.id for n in graph.nodes if n.is_seed][:3]
    for entity_id in entity_ids:
        if entity_id in by_id and entity_id not in chosen and len(chosen) < MAX_NODES:
            chosen.append(entity_id)
    for node in sorted(graph.nodes, key=lambda n: -n.score):
        if len(chosen) >= MAX_NODES:
            break
        touches = any({e.source, e.target} == {node.id, c} for e in graph.edges for c in chosen)
        if node.id not in chosen and touches:
            chosen.append(node.id)
    nodes = [
        {"id": i, "label": by_id[i].name, "type": by_id[i].type, "confidence": None}
        for i in chosen
        if i in by_id
    ]
    links = [
        {"source": e.source, "target": e.target, "predicate": e.predicate, "confidence": None}
        for e in graph.edges
        if e.source in chosen and e.target in chosen
    ]
    return nodes, links


def build_local_entry(deps, index, question: str, saved: dict) -> tuple[dict | None, str]:
    """One replay entry from a saved local answer. Returns (entry, "") or (None, reason)."""
    early, context, link = prepare_local(deps, question)
    if context is None:
        return None, "context is now a refusal or a clarify request"
    check = check_citations(saved["text"], context, index)
    if check.status != saved["check"] or check.unknown_labels:
        return None, f"citation check changed ({saved['check']} -> {check.status})"
    labels = list(dict.fromkeys(check.cited))
    shown = context.by_label()
    if any(label not in shown for label in labels):
        return None, "a cited label is missing from the rebuilt context"
    unit_ids = [shown[label].ref for label in labels if label[0] == "T"]
    rows = deps.unit_rows(unit_ids)
    citations = []
    for label in labels:
        item = shown[label]
        row = rows.get(item.ref, {}) if label[0] == "T" else {}
        citations.append(
            {
                "label": label,
                "kind": KIND_OF_LABEL[label[0]],
                "title": row.get("title") or _title(item.text),
                "text": item.text,
                "source": row.get("section") or None,
                "ref_id": item.ref,
            }
        )
    graph = deps.subgraph(link)
    nodes, links = pick_graph(graph, [shown[x].ref for x in labels if x[0] == "E"])
    return {
        "mode": "local",
        "status": "answered",
        "text": saved["text"],
        "citations": citations,
        "nodes": nodes,
        "links": links,
        "check_status": saved["check"],
        "model": "gpt-4.1-mini (saved run)",
    }, ""


def build_refusal_entry(deps, question: str) -> tuple[dict | None, str]:
    early, context, _ = prepare_local(deps, question)
    if early is None or early.status == "answered":
        return None, "the question is not refused by the free checks"
    message = early.reason + (f" {early.suggestion}" if early.suggestion else "")
    return {
        "mode": "local",
        "status": early.status,
        "message": message.strip(),
        "model": "none",
    }, ""


def baseline_entry(saved: dict) -> dict:
    return {
        "mode": "baseline",
        "status": "answered" if saved["status"] == "answered" else "refused",
        "text": saved["text"],
        "model": "gpt-4.1-mini (saved run)",
    }
