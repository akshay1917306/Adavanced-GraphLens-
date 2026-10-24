"""Tests for the hierarchical communities. The graphs are small made-up ones; nothing calls a
model. The integration tests use the real Neo4j with a throwaway index version."""

from __future__ import annotations

import os
import uuid

import pytest

pytest.importorskip("graspologic_native")

from graphlens_pipeline.communities import (  # noqa: E402
    Community,
    CommunityError,
    aggregate_edges,
    community_id,
    detect,
    frontier,
    read_communities,
    summary,
    verify_hierarchy,
    write_communities,
)


def block(prefix, size):
    """A fully connected group of `size` entities."""
    ids = [f"{prefix}{i:02d}" for i in range(size)]
    return ids, [(a, b, 1.0) for i, a in enumerate(ids) for b in ids[i + 1 :]]


def graph(*blocks, bridges=(), lonely=(), pair=None):
    ids, edges = [], []
    for ids_, edges_ in blocks:
        ids += ids_
        edges += edges_
    ids += list(lonely)
    if pair:
        ids += list(pair)
        edges.append((pair[0], pair[1], 1.0))
    edges += [(a, b, 0.1) for a, b in bridges]
    return ids, edges


def test_ids_come_from_the_members_not_their_order():
    assert community_id(0, ["b", "a"]) == community_id(0, ["a", "b"])
    assert community_id(0, ["a", "b"]) != community_id(1, ["a", "b"])


def test_edges_are_merged_undirected_and_bad_ones_dropped():
    out = aggregate_edges([("b", "a", 1.0), ("a", "b", 2.0), ("a", "a", 5.0), ("a", "c", 0.0)])
    assert out == [("a", "b", 3.0)]


def test_two_dense_groups_become_two_communities_and_loners_get_their_own():
    a, b = block("a", 8), block("b", 8)
    ids, edges = graph(a, b, bridges=[("a00", "b00")], lonely=["x"], pair=("p1", "p2"))
    found = detect(ids, edges, max_cluster_size=100)
    level0 = [c for c in found if c.level == 0]
    sizes = sorted(c.size for c in level0)
    assert sizes == [1, 2, 8, 8]
    assert verify_hierarchy(found, ids) == []
    stubs = {c.size for c in found if c.is_stub}
    assert stubs == {1, 2}


def test_the_same_graph_and_seed_give_the_same_result_in_any_input_order():
    ids, edges = graph(block("a", 10), block("b", 10), bridges=[("a00", "b00")])
    first = detect(ids, edges)
    second = detect(list(reversed(ids)), list(reversed(edges)))
    assert [(c.id, c.level, c.parent_id) for c in first] == [
        (c.id, c.level, c.parent_id) for c in second
    ]


def layered(blocks=3, subs=3, size=10):
    """`blocks` loose groups, each made of `subs` tight groups of `size` entities. The links are
    picked by position, not at random, so the test graph is always the same."""
    ids = [f"b{b}s{s}n{i:02d}" for b in range(blocks) for s in range(subs) for i in range(size)]
    where = {n: (int(n[1]), int(n[3])) for n in ids}
    edges = []
    for i, a in enumerate(ids):
        for j in range(i + 1, len(ids)):
            c = ids[j]
            (ba, sa), (bc, sc) = where[a], where[c]
            if ba == bc and sa == sc:
                edges.append((a, c, 1.0))
            elif ba == bc and (i + j) % 3 == 0:
                edges.append((a, c, 0.5))
            elif ba != bc and (i * 7 + j) % 40 == 0:
                edges.append((a, c, 0.05))
    return ids, edges


def test_big_groups_are_split_into_a_tree_that_covers_every_entity_once():
    ids, edges = layered()
    found = detect(ids, edges, max_cluster_size=20)
    levels = {lvl: sorted(c.size for c in found if c.level == lvl) for lvl in (0, 1)}
    assert levels[0] == [30, 30, 30] and levels[1] == [10] * 9
    assert verify_hierarchy(found, ids) == []
    for level in (0, 1):
        covered = [m for c in frontier(found, level) for m in c.members]
        assert sorted(covered) == sorted(ids)  # every entity exactly once at every level
    assert all(not c.is_leaf for c in found if c.level == 0)
    assert summary(found)["communities"] == len(found) == 12


def test_an_edge_to_an_unknown_entity_is_refused():
    with pytest.raises(CommunityError):
        detect(["a"], [("a", "ghost", 1.0)])


def test_no_edges_at_all_still_gives_every_entity_a_community():
    found = detect(["a", "b", "c"], [])
    assert [c.size for c in found] == [1, 1, 1] and verify_hierarchy(found, ["a", "b", "c"]) == []


def test_the_checker_finds_missing_entities_and_children_that_do_not_add_up():
    parent = Community("p", 0, ["a", "b", "c"], children=["k"])
    child = Community("k", 1, ["a", "b"], parent_id="p")
    problems = verify_hierarchy([parent, child], ["a", "b", "c", "d"])
    assert any("no level-0 community" in p for p in problems)
    assert any("do not cover exactly" in p for p in problems)


# --- the real Neo4j ---------------------------------------------------------------------


@pytest.fixture
def driver():
    from neo4j import GraphDatabase

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        pytest.skip("NEO4J_* is not set")
    from graphlens_pipeline.graphstore import apply_schema

    with GraphDatabase.driver(uri, auth=(user, password)) as drv:
        apply_schema(drv)
        yield drv


@pytest.fixture
def version(driver):
    name = f"test-{uuid.uuid4().hex[:8]}"
    yield name
    with driver.session() as session:
        session.run("MATCH (c:Community {index_version: $v}) DETACH DELETE c", v=name).consume()
        session.run("MATCH (e:Entity {index_version: $v}) DETACH DELETE e", v=name).consume()


def make_entities(driver, ids, version):
    with driver.session() as session:
        session.run(
            "UNWIND $ids AS id MERGE (e:Entity {id: id}) SET e.index_version = $v",
            ids=ids, v=version,
        ).consume()  # fmt: skip


@pytest.mark.integration
def test_writing_twice_gives_the_same_graph_and_reads_back_whole(driver, version):
    ids, edges = layered(blocks=2)
    ids = ids + ["lonely"]
    ids = [f"{version}:{i}" for i in ids]
    edges = [(f"{version}:{a}", f"{version}:{b}", w) for a, b, w in edges]
    make_entities(driver, ids, version)
    found = detect(ids, edges, max_cluster_size=20)
    write_communities(driver, found, version, seed=42, max_cluster_size=20)
    write_communities(driver, found, version, seed=42, max_cluster_size=20)
    stored = read_communities(driver, version)
    assert [(c.id, c.level, c.parent_id, c.members) for c in stored] == [
        (c.id, c.level, c.parent_id, c.members) for c in found
    ]
    assert verify_hierarchy(stored, ids) == []


@pytest.mark.integration
def test_a_second_write_removes_communities_that_no_longer_exist(driver, version):
    ids = [f"{version}:{i}" for i in "abcd"]
    make_entities(driver, ids, version)
    write_communities(driver, detect(ids, []), version, seed=1, max_cluster_size=50)
    assert len(read_communities(driver, version)) == 4
    merged = detect(ids, [(ids[0], ids[1], 1.0), (ids[1], ids[2], 1.0), (ids[0], ids[2], 1.0)])
    write_communities(driver, merged, version, seed=1, max_cluster_size=50)
    stored = read_communities(driver, version)
    assert sorted(c.size for c in stored) == [1, 3]
    assert verify_hierarchy(stored, ids) == []
