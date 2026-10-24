"""Tests for the graph quality checks. The graph data here is made up (clearly labelled mock
dicts shaped like what Neo4j returns); nothing calls a model."""

from __future__ import annotations

import pytest

from graphlens_pipeline import quality
from graphlens_pipeline.quality import Check, compute_checks, likely_duplicates, render_report
from tests.test_resolve import ONTOLOGY


def ent(eid, name, type_="Method", degree=1, mentions=1, sources=("u1",), embedded=True):
    return {
        "id": eid, "name": name, "type": type_, "mentions": mentions,
        "sources": list(sources), "embedded": embedded, "degree": degree,
    }  # fmt: skip


def edge(predicate="EVALUATED_ON", a="Method", b="Dataset", evidence=("u1",)):
    return {"predicate": predicate, "from_type": a, "to_type": b, "evidence": list(evidence)}


STATS = {"units": 100, "failed": 0, "relations": 90, "rejected": {"type_not_allowed": 10}}


@pytest.fixture
def units_exist(monkeypatch):
    monkeypatch.setattr(quality, "_existing_units", lambda engine, ids: {"u1", "u2"} & set(ids))


def by_name(checks):
    return {c.name: c for c in checks}


def test_a_check_passes_in_the_right_direction():
    assert Check("x", 0.99, 0.99, True).passed and not Check("x", 0.98, 0.99, True).passed
    assert Check("x", 0.10, 0.10, False).passed and not Check("x", 0.11, 0.10, False).passed


def test_obvious_duplicates_are_found_but_numbers_and_unrelated_names_are_not():
    names = ["Dense Passage Retrieval", "DPR", "beam search", "beam search algorithm"]
    pairs = likely_duplicates([ent(str(i), n) for i, n in enumerate(names)])
    assert ("Dense Passage Retrieval", "DPR") in pairs
    assert ("beam search", "beam search algorithm") in pairs
    none = likely_duplicates([ent("1", "SQuAD", "Dataset"), ent("2", "SQuAD 2", "Dataset")])
    assert none == []
    other = likely_duplicates([ent("1", "BERT"), ent("2", "T5"), ent("3", "reranking")])
    assert other == []


def test_orphans_are_counted_by_type_and_missing_evidence_fails(units_exist):
    entities = [ent("1", "A", degree=0, mentions=1), ent("2", "B", "Dataset"), ent("3", "C")]
    edges = [edge(), edge(evidence=("u1", "u-missing")), edge(evidence=())]
    checks = by_name(compute_checks(entities, edges, STATS, ONTOLOGY, engine=None))
    assert round(checks["orphan_rate"].value, 3) == round(1 / 3, 3)
    assert checks["orphan_rate"].details["by_type"] == {"Method": 1}
    assert not checks["orphan_rate"].passed
    assert round(checks["edge_evidence"].value, 3) == round(1 / 3, 3)
    assert not checks["edge_evidence"].passed and checks["node_provenance"].passed


def test_edges_the_ontology_does_not_allow_are_counted(units_exist):
    entities = [ent("1", "A"), ent("2", "B", "Dataset")]
    checks = by_name(
        compute_checks(entities, [edge(), edge("EVALUATED_ON", "Dataset", "Method")], STATS,
                       ONTOLOGY, engine=None)
    )  # fmt: skip
    assert checks["ontology_conformance"].value == 0.5


def test_schema_validity_reports_how_many_relations_the_second_check_dropped(units_exist):
    stats = {**STATS, "failed": 2}
    check = by_name(compute_checks([ent("1", "A")], [], stats, ONTOLOGY, engine=None))
    assert check["schema_validity"].value == 0.98 and not check["schema_validity"].passed
    assert check["schema_validity"].details["dropped_share"] == 0.1


def test_the_report_names_what_is_not_measured_and_marks_misses(units_exist):
    checks = compute_checks([ent("1", "A", degree=0)], [], STATS, ONTOLOGY, engine=None)
    report = render_report(checks, "idx-test")
    assert "**MISS**" in report and "Not measured yet" in report
    assert "relation_precision" in report and "entity_resolution_f1" in report


@pytest.mark.integration
def test_saved_checks_replace_earlier_ones_of_the_same_name(engine, tmp_path):
    from sqlalchemy import text

    from graphlens_pipeline.runs import start_run
    from tests.test_embed import prepare

    prepare(engine, tmp_path)
    run = start_run(engine, "embed corpus", "idx-quality-test", {}, 1.0, sample=True)
    quality.save_checks(engine, str(run.id), [Check("orphan_rate", 0.2, 0.1, False)])
    quality.save_checks(engine, str(run.id), [Check("orphan_rate", 0.05, 0.1, False)])
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT value, passed FROM quality_checks WHERE run_id = :r"), {"r": run.id}
        ).all()
    assert [(float(v), p) for v, p in rows] == [(0.05, True)]
