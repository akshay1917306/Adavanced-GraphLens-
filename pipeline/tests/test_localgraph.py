"""Tests for graph expansion and PageRank. Small made-up graphs; the expansion tests run against
the real Neo4j with a throwaway index version. No model is called."""

from __future__ import annotations

import math
import uuid

import pytest

from graphlens_pipeline.graphstore import GraphLoadError
from graphlens_pipeline.linking import Linked
from graphlens_pipeline.localgraph import (
    Edge,
    Node,
    Subgraph,
    build_expand_query,
    build_subgraph,
    cosine,
    evidence_coverage,
    expand,
    fetch_edges,
    personalized_pagerank,
    score_nodes,
)

PREDICATES = ["USES", "EVALUATED_ON"]

# --- the expansion query ----------------------------------------------------------------------


def test_the_query_uses_only_ontology_relation_types_and_a_checked_hop_count():
    query = build_expand_query(PREDICATES, 2)
    assert "[:USES|EVALUATED_ON*1..2]" in query and "$seeds" in query and "$limit" in query
    assert "IN_COMMUNITY" not in query and "CHILD_OF" not in query
    for bad_hops in (0, 4, "2", None):
        with pytest.raises(GraphLoadError):
            build_expand_query(PREDICATES, bad_hops)
    with pytest.raises(GraphLoadError):
        build_expand_query(["USES) DETACH DELETE n //"], 2)


# --- PageRank ---------------------------------------------------------------------------------


def chain(n=4):
    ids = [f"n{i}" for i in range(n)]
    return ids, [(ids[i], ids[i + 1], 1.0) for i in range(n - 1)]


def test_scores_fall_with_distance_from_the_seed_and_add_up_to_one():
    ids, edges = chain(5)
    rank = personalized_pagerank(ids, edges, {"n0": 1.0})
    assert math.isclose(sum(rank.values()), 1.0, rel_tol=1e-6)
    # the seed's neighbour collects the most (it has two links); after that, farther is lower
    assert rank["n1"] > rank["n0"] > rank["n2"] > rank["n3"] > rank["n4"]


def test_two_seeds_share_the_restart_in_proportion_to_their_weights():
    ids, edges = chain(5)
    rank = personalized_pagerank(ids, edges, {"n0": 3.0, "n4": 1.0})
    assert rank["n0"] > rank["n4"] and rank["n2"] > 0


def test_a_node_with_no_links_and_unknown_nodes_do_not_break_it():
    ids, edges = chain(3)
    rank = personalized_pagerank(ids + ["lonely"], edges + [("n0", "ghost", 1.0)], {"n0": 1.0})
    assert math.isclose(sum(rank.values()), 1.0, rel_tol=1e-6)
    assert rank["lonely"] < rank["n1"]
    assert personalized_pagerank([], [], {}) == {}
    only = personalized_pagerank(["a", "b"], [], {"a": 1.0})
    assert only["a"] > only["b"] and math.isclose(sum(only.values()), 1.0)


def test_the_result_is_the_same_every_time():
    ids, edges = chain(6)
    assert personalized_pagerank(ids, edges, {"n1": 1.0}) == personalized_pagerank(
        ids, edges, {"n1": 1.0}
    )


# --- scoring and keeping -----------------------------------------------------------------------


def node(i, seed=False, hops=1):
    return Node(f"n{i}", f"Name {i}", "Method", "", [f"u_{i:012d}_0001"], 1, hops, seed)


def test_the_best_nodes_are_kept_and_a_seed_is_never_dropped():
    nodes = [node(0, seed=True, hops=0)] + [node(i) for i in range(1, 8)]
    edges = [Edge(f"n{i}", f"n{i + 1}", "USES", "", 1.0, []) for i in range(7)]
    vectors = {f"n{i}": [1.0, float(i)] for i in range(8)}
    kept = score_nodes(nodes, edges, vectors, [1.0, 0.0], {"n0": 1.0}, keep=3)
    assert len(kept) == 3 and kept[0].id == "n0" and kept[0].is_seed
    far_seed = [node(0, hops=0), node(1, seed=True, hops=0)] + [node(i) for i in range(2, 6)]
    edges2 = [Edge("n0", f"n{i}", "USES", "", 1.0, []) for i in range(2, 6)]
    kept2 = score_nodes(far_seed, edges2, {}, [1.0, 0.0], {"n1": 1.0}, keep=2)
    assert "n1" in {n.id for n in kept2}  # a seed with no links survives


def test_with_no_pagerank_share_only_similarity_ranks():
    nodes = [node(0, seed=True, hops=0), node(1), node(2)]
    vectors = {"n0": [1.0, 0.0], "n1": [0.0, 1.0], "n2": [1.0, 0.1]}
    kept = score_nodes(nodes, [], vectors, [1.0, 0.0], {"n0": 1.0}, keep=3, ppr_share=0.0)
    assert [n.id for n in kept] == ["n0", "n2", "n1"]


def test_cosine_and_evidence_coverage():
    assert cosine([1, 0], [1, 0]) == 1.0 and cosine([1, 0], [0, 1]) == 0.0
    assert cosine([0, 0], [1, 1]) == 0.0
    graph = Subgraph([node(1), node(2)], [Edge("n1", "n2", "USES", "", 1.0, ["u_x"])])
    assert evidence_coverage(graph, {"u_000000000001_0001", "u_x", "u_missing"}) == pytest.approx(
        2 / 3
    )
    assert math.isnan(evidence_coverage(graph, set()))


# --- the real Neo4j ---------------------------------------------------------------------------


@pytest.fixture
def driver_and_version():
    import os

    from neo4j import GraphDatabase

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        pytest.skip("NEO4J_* is not set")
    from graphlens_pipeline.graphstore import apply_schema

    version = f"test-{uuid.uuid4().hex[:8]}"
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        apply_schema(driver)
        yield driver, version
        with driver.session() as session:
            session.run("MATCH (e:Entity {index_version: $v}) DETACH DELETE e", v=version).consume()
            session.run(
                "MATCH (c:Community {index_version: $v}) DETACH DELETE c", v=version
            ).consume()


def make_graph(driver, version):
    """a -USES-> b -USES-> c -USES-> d, plus a community that contains a and z (no relation)."""
    ids = {name: f"{version}-{name}" for name in "abcdz"}
    with driver.session() as session:
        for name, eid in ids.items():
            session.run(
                "CREATE (e:Entity {id: $id, name: $name, type: 'Method', index_version: $v,"
                " mention_count: 1, source_unit_ids: [$unit], description: 'd'})"
                " WITH e CALL db.create.setNodeVectorProperty(e, 'embedding', $vec)",
                id=eid, name=name, v=version, unit=f"u_{name}_0001", vec=[1.0, 0.1] + [0.0] * 766,
            ).consume()  # fmt: skip
        for a, b in (("a", "b"), ("b", "c"), ("c", "d")):
            session.run(
                "MATCH (x:Entity {id: $a}), (y:Entity {id: $b})"
                " CREATE (x)-[:USES {weight: 1.0, description: 'r', evidence_unit_ids: [$u],"
                " index_version: $v}]->(y)",
                a=ids[a], b=ids[b], u=f"u_{a}{b}_0001", v=version,
            ).consume()  # fmt: skip
        session.run(
            "MATCH (x:Entity {id: $a}), (z:Entity {id: $z})"
            " CREATE (c:Community {id: $cid, index_version: $v}),"
            " (x)-[:IN_COMMUNITY {level: 0}]->(c), (z)-[:IN_COMMUNITY {level: 0}]->(c)",
            a=ids["a"], z=ids["z"], cid=f"{version}-community", v=version,
        ).consume()  # fmt: skip
    return ids


@pytest.mark.integration
def test_expansion_follows_relations_by_hops_and_never_goes_through_a_community(driver_and_version):
    driver, version = driver_and_version
    ids = make_graph(driver, version)
    one = expand(driver, [ids["a"]], PREDICATES, version, max_hops=1)
    two = expand(driver, [ids["a"]], PREDICATES, version, max_hops=2)
    assert one == {ids["a"]: 0, ids["b"]: 1}
    assert two == {ids["a"]: 0, ids["b"]: 1, ids["c"]: 2}
    assert ids["z"] not in two  # z is only reachable through the community
    assert len(expand(driver, [ids["a"]], PREDICATES, version, max_hops=3, limit=1)) == 2
    assert expand(driver, [], PREDICATES, version) == {}
    assert expand(driver, [ids["a"]], PREDICATES, "another-version") == {ids["a"]: 0}


@pytest.mark.integration
def test_the_subgraph_has_nodes_edges_among_them_and_coverage(driver_and_version):
    driver, version = driver_and_version
    ids = make_graph(driver, version)
    seeds = [Linked(ids["a"], "a", "Method", 1.0, "name")]
    graph = build_subgraph(driver, seeds, [1.0, 0.1] + [0.0] * 766, PREDICATES, version, max_hops=2)
    assert {n.id for n in graph.nodes} == {ids["a"], ids["b"], ids["c"]}
    assert graph.nodes[0].is_seed and graph.candidates == 3
    assert {(e.source, e.target) for e in graph.edges} == {
        (ids["a"], ids["b"]), (ids["b"], ids["c"])
    }  # fmt: skip
    assert evidence_coverage(graph, {"u_ab_0001", "u_bc_0001", "u_cd_0001"}) == pytest.approx(2 / 3)
    assert build_subgraph(driver, [], [1.0], PREDICATES, version).nodes == []
    edges = fetch_edges(driver, list(ids.values()), PREDICATES, version)
    assert len(edges) == 3 and all(e.evidence for e in edges)
