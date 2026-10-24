"""Tests for the Neo4j load. The integration tests use the real Neo4j of the compose stack and
a throwaway index version that is removed afterwards. Nothing here calls a model."""

from __future__ import annotations

import os
import uuid

import pytest

from graphlens_pipeline.graphstore import (
    EMBEDDING_DIMENSIONS,
    GraphLoadError,
    _checked,
    _statements,
    apply_schema,
    check_provenance,
    count_graph,
    embedding_text,
    load_graph,
    relation_key,
    schema_scripts,
)
from graphlens_pipeline.resolve import Resolution, ResolvedEntity, ResolvedRelation
from tests.test_resolve import ONTOLOGY


def entity(eid, name, type_="Method", sources=("u1",)):
    return ResolvedEntity(eid, name, type_, [name.lower()], f"{name} desc", 1, list(sources))


def relation(a, p, b, evidence=("u1",)):
    return ResolvedRelation(a, p, b, "d", 1.0, 0.9, list(evidence))


def resolution(entities, relations):
    return Resolution(entities=entities, relations=relations, decisions=[])


def vec(i):
    row = [0.0] * EMBEDDING_DIMENSIONS
    row[i % EMBEDDING_DIMENSIONS] = 1.0
    return row


# --- no database needed ---------------------------------------------------------------------


def test_labels_and_relationship_types_must_come_from_the_ontology():
    assert _checked("Method", ONTOLOGY.type_names) == "Method"
    for bad in ("Method) DETACH DELETE n //", "Unknown", "method", ""):
        with pytest.raises(GraphLoadError):
            _checked(bad, ONTOLOGY.type_names)


def test_schema_scripts_are_numbered_and_split_into_statements():
    scripts = schema_scripts()
    assert [v for v, _, _ in scripts] == sorted(v for v, _, _ in scripts)
    assert scripts[0][0].startswith("V001")
    assert all(len(checksum) == 16 for _, checksum, _ in scripts)
    statements = [s for _, _, body in scripts for s in _statements(body)]
    assert statements and all(s.startswith("CREATE") for s in statements)


def test_every_entity_needs_a_source_and_every_edge_needs_evidence():
    ok = resolution([entity("a", "A"), entity("b", "B")], [relation("a", "ADDRESSES", "b")])
    check_provenance(ok)
    with pytest.raises(GraphLoadError, match="no source"):
        check_provenance(resolution([entity("a", "A", sources=())], []))
    with pytest.raises(GraphLoadError, match="no evidence"):
        check_provenance(
            resolution([entity("a", "A"), entity("b", "B")], [relation("a", "X", "b", ())])
        )
    with pytest.raises(GraphLoadError, match="missing entity"):
        check_provenance(resolution([entity("a", "A")], [relation("a", "X", "zzz")]))


def test_a_load_without_a_vector_is_refused_before_touching_the_database():
    with pytest.raises(GraphLoadError, match="vector"):
        load_graph(None, resolution([entity("a", "A")], []), ONTOLOGY, {}, "v")


def test_relation_keys_and_embedding_text():
    assert relation_key("a", "USES", "b") == "a|USES|b"
    assert embedding_text("DPR", "") == "DPR"
    assert embedding_text("DPR", "x" * 1000).startswith("DPR: x") and len(
        embedding_text("DPR", "x" * 1000)
    ) == 400


# --- the real Neo4j -----------------------------------------------------------------------


@pytest.fixture
def driver():
    from neo4j import GraphDatabase

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        pytest.skip("NEO4J_* is not set")
    with GraphDatabase.driver(uri, auth=(user, password)) as drv:
        yield drv


@pytest.fixture
def version(driver):
    name = f"test-{uuid.uuid4().hex[:8]}"
    yield name
    with driver.session() as session:  # only the throwaway nodes of this test
        session.run("MATCH (e:Entity {index_version: $v}) DETACH DELETE e", v=name).consume()


@pytest.mark.integration
def test_schema_is_applied_once_and_has_the_vector_index(driver):
    apply_schema(driver)
    assert apply_schema(driver) == []  # second time: nothing left to do
    with driver.session() as session:
        names = {r["name"] for r in session.run("SHOW INDEXES YIELD name")}
        constraints = {r["name"] for r in session.run("SHOW CONSTRAINTS YIELD name")}
    assert {"entity_embedding", "entity_type", "entity_text"} <= names
    assert "entity_id" in constraints


@pytest.mark.integration
def test_load_writes_labels_edges_and_provenance_and_is_idempotent(driver, version):
    apply_schema(driver)
    data = resolution(
        [entity("t1", "DPR"), entity("t2", "NQ", "Dataset"), entity("t3", "Open QA", "Task")],
        [
            relation("t1", "EVALUATED_ON", "t2", ("u1", "u2")),
            relation("t1", "ADDRESSES", "t3"),
        ],
    )
    vectors = {"t1": vec(0), "t2": vec(1), "t3": vec(2)}
    first = load_graph(driver, data, ONTOLOGY, vectors, version)
    second = load_graph(driver, data, ONTOLOGY, vectors, version)
    assert first == second
    assert (first.entities, first.relations, first.with_embedding) == (3, 2, 3)
    assert first.entities_by_type == {"Method": 1, "Dataset": 1, "Task": 1}
    with driver.session() as session:
        row = session.run(
            "MATCH (m:Method {id: 't1'})-[r:EVALUATED_ON]->(d:Dataset) "
            "RETURN r.evidence_unit_ids AS evidence, m.source_unit_ids AS sources, "
            "m.aliases AS aliases, d.name AS dataset"
        ).single()
    assert row["evidence"] == ["u1", "u2"] and row["sources"] == ["u1"]
    assert row["aliases"] == ["dpr"] and row["dataset"] == "NQ"


@pytest.mark.integration
def test_a_second_load_removes_what_the_first_wrote_and_this_one_did_not(driver, version):
    apply_schema(driver)
    full = resolution(
        [entity("t1", "DPR"), entity("t2", "NQ", "Dataset")],
        [relation("t1", "EVALUATED_ON", "t2")],
    )
    load_graph(driver, full, ONTOLOGY, {"t1": vec(0), "t2": vec(1)}, version)
    smaller = resolution([entity("t1", "DPR")], [])
    counts = load_graph(driver, smaller, ONTOLOGY, {"t1": vec(0)}, version)
    assert (counts.entities, counts.relations) == (1, 0)


@pytest.mark.integration
def test_the_vector_index_finds_the_nearest_entity(driver, version):
    apply_schema(driver)
    data = resolution([entity("t1", "DPR"), entity("t2", "BM25")], [])
    load_graph(driver, data, ONTOLOGY, {"t1": vec(0), "t2": vec(1)}, version)
    with driver.session() as session:
        rows = list(
            session.run(
                "CALL db.index.vector.queryNodes('entity_embedding', 2, $q) YIELD node, score "
                "WHERE node.index_version = $v RETURN node.name AS name ORDER BY score DESC",
                q=vec(0), v=version,
            )
        )  # fmt: skip
    assert rows and rows[0]["name"] == "DPR"
    assert count_graph(driver, version).with_embedding == 2
