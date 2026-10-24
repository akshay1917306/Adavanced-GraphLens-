"""Quality gate checks for the graph, read from Neo4j and Postgres.

Only checks that can be measured without human labels are computed here. Precision of relations
and the entity-resolution F1 need the labeled sets (step 9) and are reported as "not measured",
never guessed. Nothing here calls a model.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import Engine, text

from graphlens_pipeline.ontology import Ontology
from graphlens_pipeline.resolve import _core_tokens, _is_acronym_of, blocked_by_rules

NOT_MEASURED = {
    "relation_precision": "needs the 30 labeled text units (step 9); target 0.80",
    "entity_resolution_f1": "needs the labeled candidate pairs (step 9); target 0.85",
    "duplicate_rate_audit": "needs the owner's sample audit; the automatic number below is a proxy",
    "communities": "Phase 3",
}


@dataclass
class Check:
    name: str
    value: float
    threshold: float
    higher_is_better: bool
    details: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        if self.higher_is_better:
            return self.value >= self.threshold
        return self.value <= self.threshold


def read_graph(driver, index_version: str, database: str = "neo4j") -> tuple[list, list]:
    """(entities, edges) of one index version as plain dicts."""
    with driver.session(database=database) as session:
        entities = [
            dict(r)
            for r in session.run(
                "MATCH (e:Entity {index_version: $v}) RETURN e.id AS id, e.name AS name,"
                " e.type AS type, e.mention_count AS mentions, e.source_unit_ids AS sources,"
                " e.embedding IS NOT NULL AS embedded, COUNT { (e)--() } AS degree",
                v=index_version,
            )
        ]  # fmt: skip
        edges = [
            dict(r)
            for r in session.run(
                "MATCH (a:Entity)-[r]->(b:Entity) WHERE r.index_version = $v"
                " RETURN type(r) AS predicate, a.type AS from_type, b.type AS to_type,"
                " r.evidence_unit_ids AS evidence",
                v=index_version,
            )
        ]  # fmt: skip
    return entities, edges


def _existing_units(engine: Engine, ids: set[str]) -> set[str]:
    if not ids:
        return set()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id FROM text_units WHERE id = ANY(:ids)"), {"ids": list(ids)}
        )
        return {r[0] for r in rows}


def likely_duplicates(entities: list[dict]) -> list[tuple[str, str]]:
    """Same-type pairs that look like one thing: an acronym and its long form, or the same
    words apart from generic ones. An automatic proxy, not an audit."""
    by_type: dict[str, list[dict]] = {}
    for entity in entities:
        by_type.setdefault(entity["type"], []).append(entity)
    pairs = []
    for group in by_type.values():
        cores = [(e, _core_tokens(e["name"])) for e in group]
        for i, (a, core_a) in enumerate(cores):
            for b, core_b in cores[i + 1 :]:
                if blocked_by_rules(a["name"], b["name"]):
                    continue
                same_words = bool(core_a) and core_a == core_b
                if (
                    same_words
                    or _is_acronym_of(a["name"], b["name"])
                    or _is_acronym_of(b["name"], a["name"])
                ):
                    pairs.append((a["name"], b["name"]))
    return pairs


def compute_checks(
    entities: list[dict], edges: list[dict], run_stats: dict, ontology: Ontology, engine: Engine
) -> list[Check]:
    total = max(len(entities), 1)
    units = max(run_stats.get("units", 0), 1)
    rejected = run_stats.get("rejected", {})
    kept, dropped = run_stats.get("relations", 0), sum(rejected.values())

    known = _existing_units(
        engine,
        {u for e in entities for u in e["sources"] or []}
        | {u for r in edges for u in r["evidence"] or []},
    )
    nodes_ok = sum(1 for e in entities if e["sources"] and set(e["sources"]) <= known)
    edges_ok = sum(1 for r in edges if r["evidence"] and set(r["evidence"]) <= known)
    allowed = sum(1 for r in edges if ontology.allows(r["predicate"], r["from_type"], r["to_type"]))
    isolated = [e for e in entities if e["degree"] == 0]
    duplicates = likely_duplicates(entities)
    in_pairs = {n for pair in duplicates for n in pair}

    return [
        Check(
            "schema_validity",
            (units - run_stats.get("failed", 0)) / units,
            0.99,
            True,
            {
                "units": units,
                "failed_units": run_stats.get("failed", 0),
                "relations_kept_by_the_second_check": kept,
                "relations_dropped_by_the_second_check": dropped,
                "dropped_by_reason": rejected,
                "dropped_share": round(dropped / max(kept + dropped, 1), 3),
            },
        ),  # fmt: skip
        Check(
            "node_provenance",
            nodes_ok / total,
            1.0,
            True,
            {"entities": len(entities), "with_existing_source_units": nodes_ok},
        ),
        Check(
            "edge_evidence",
            edges_ok / max(len(edges), 1),
            1.0,
            True,
            {"edges": len(edges), "with_existing_evidence_units": edges_ok},
        ),
        Check(
            "ontology_conformance",
            allowed / max(len(edges), 1),
            1.0,
            True,
            {"edges": len(edges), "allowed_by_ontology": allowed},
        ),
        Check(
            "embedding_coverage",
            sum(1 for e in entities if e["embedded"]) / total,
            1.0,
            True,
            {"entities": len(entities)},
        ),
        Check(
            "duplicate_rate_proxy",
            len(in_pairs) / total,
            0.05,
            False,
            {
                "kind": "automatic proxy, not the owner's audit",
                "pairs": len(duplicates),
                "entities_involved": len(in_pairs),
                "examples": duplicates[:15],
            },
        ),  # fmt: skip
        Check(
            "orphan_rate",
            len(isolated) / total,
            0.10,
            False,
            {
                "isolated": len(isolated),
                "entities": len(entities),
                "by_type": dict(Counter(e["type"] for e in isolated)),
                "single_mention": sum(1 for e in isolated if (e["mentions"] or 0) <= 1),
            },
        ),  # fmt: skip
    ]


def save_checks(engine: Engine, run_id: str, checks: list[Check]) -> None:
    """Store the checks of this run; an earlier result with the same name is replaced."""
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM quality_checks WHERE run_id = :r AND check_name = ANY(:n)"),
            {"r": run_id, "n": [c.name for c in checks]},
        )
        for check in checks:
            conn.execute(
                text(
                    "INSERT INTO quality_checks (run_id, check_name, value, threshold, passed,"
                    " details) VALUES (:r, :n, :v, :t, :p, CAST(:d AS jsonb))"
                ),
                {"r": run_id, "n": check.name, "v": round(check.value, 4),
                 "t": check.threshold, "p": check.passed, "d": json.dumps(check.details)},
            )  # fmt: skip


def render_report(checks: list[Check], index_version: str) -> str:
    lines = [
        f"# Quality report: {index_version}",
        "",
        "Measured by `quality-report` on the graph in Neo4j. Numbers only; no model was called.",
        "",
        "| Check | Value | Target | Result |",
        "|---|---|---|---|",
    ]
    for c in checks:
        sign = ">=" if c.higher_is_better else "<="
        lines.append(
            f"| {c.name} | {c.value:.1%} | {sign} {c.threshold:.0%} | "
            f"{'PASS' if c.passed else '**MISS**'} |"
        )
    lines += ["", "## Not measured yet", ""]
    lines += [f"- **{name}**: {why}" for name, why in NOT_MEASURED.items()]
    for c in checks:
        body = json.dumps(c.details, indent=2)
        lines += ["", f"## Details: {c.name}", "", "```json", body, "```"]
    return "\n".join(lines) + "\n"
