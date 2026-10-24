"""Hierarchical communities over the entity graph, written to Neo4j.

How the levels work: Leiden first groups all entities (level 0). A group larger than
`max_cluster_size` is split again (level 1), and so on. A group that is small enough is not split,
so it is a *leaf* at the level where it appears. Entities with no relation cannot be clustered;
each becomes its own level-0 community (a leaf, and a stub because it is tiny).

Safety rules as in `graphstore.py`: fixed query templates with parameters only, no model-written
Cypher. Writing is idempotent: community IDs come from their members, so the same graph and seed
give the same IDs, and what an earlier run of the same index version wrote but this run did not
is removed.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field

SEED = 42
MAX_CLUSTER_SIZE = 50
STUB_SIZE = 3  # communities with fewer entities get a stub report without a model (D29)
BATCH = 500


class CommunityError(Exception):
    pass


@dataclass
class Community:
    id: str
    level: int
    members: list[str]  # entity IDs, sorted
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def is_leaf(self) -> bool:
        return not self.children

    @property
    def is_stub(self) -> bool:
        return self.size < STUB_SIZE


def community_id(level: int, members: list[str]) -> str:
    digest = hashlib.sha1(f"{level}|{','.join(sorted(members))}".encode()).hexdigest()  # noqa: S324
    return "c_" + digest[:12]


def aggregate_edges(pairs: list[tuple[str, str, float]]) -> list[tuple[str, str, float]]:
    """Undirected weighted edges, one per pair, sorted so the input order never matters."""
    weights: Counter = Counter()
    for a, b, weight in pairs:
        if a != b and weight > 0:
            weights[tuple(sorted((a, b)))] += weight
    return [(a, b, w) for (a, b), w in sorted(weights.items())]


def detect(
    entity_ids: list[str],
    edges: list[tuple[str, str, float]],
    max_cluster_size: int = MAX_CLUSTER_SIZE,
    seed: int = SEED,
) -> list[Community]:
    """Hierarchical Leiden. Returns every community of every level, parents before children."""
    import graspologic_native as native

    edges = aggregate_edges(edges)
    known = set(entity_ids)
    connected = {n for a, b, _ in edges for n in (a, b)}
    if not connected <= known:
        raise CommunityError("an edge points at an entity that is not in the entity list")
    raw = []
    if edges:
        raw = native.hierarchical_leiden(
            edges, resolution=1.0, randomness=0.001, iterations=1, use_modularity=True,
            max_cluster_size=max_cluster_size, seed=seed,
        )  # fmt: skip

    groups: dict[tuple[int, int], set[str]] = defaultdict(set)
    parents: dict[tuple[int, int], tuple[int, int] | None] = {}
    for item in raw:
        key = (item.level, item.cluster)
        groups[key].add(item.node)
        parents[key] = (
            None if item.parent_cluster is None else (item.level - 1, item.parent_cluster)
        )

    by_key: dict[tuple[int, int], Community] = {}
    for key in sorted(groups):
        members = sorted(groups[key])
        by_key[key] = Community(community_id(key[0], members), key[0], members)
    for key, community in by_key.items():
        parent_key = parents[key]
        if parent_key is not None:
            parent = by_key.get(parent_key)
            if parent is None:
                raise CommunityError("a community points at a parent that does not exist")
            community.parent_id = parent.id
            parent.children.append(community.id)
    result = list(by_key.values())
    for entity_id in sorted(known - connected):  # no relation: its own community
        result.append(Community(community_id(0, [entity_id]), 0, [entity_id]))
    for community in result:
        community.children.sort()
    return sorted(result, key=lambda c: (c.level, c.id))


def verify_hierarchy(communities: list[Community], entity_ids: list[str]) -> list[str]:
    """Problems that would break the quality gate; an empty list means the hierarchy is sound."""
    problems = []
    by_id = {c.id: c for c in communities}
    if len(by_id) != len(communities):
        problems.append("two communities share an ID")
    top = defaultdict(list)
    for c in communities:
        if c.level == 0:
            for entity in c.members:
                top[entity].append(c.id)
    missing = set(entity_ids) - set(top)
    if missing:
        problems.append(f"{len(missing)} entities are in no level-0 community")
    twice = [e for e, ids in top.items() if len(ids) > 1]
    if twice:
        problems.append(f"{len(twice)} entities are in two level-0 communities")
    for c in communities:
        if c.children:
            union = sorted({m for child in c.children for m in by_id[child].members})
            if union != c.members:
                problems.append(f"the children of {c.id} do not cover exactly its members")
            if any(by_id[child].level != c.level + 1 for child in c.children):
                problems.append(f"{c.id} has a child that is not one level deeper")
        if c.parent_id and c.parent_id not in by_id:
            problems.append(f"{c.id} has a missing parent")
    return problems


def frontier(communities: list[Community], level: int) -> list[Community]:
    """The communities that together cover every entity once when looking at `level`:
    communities of that level, plus leaves from shallower levels that were never split."""
    return [c for c in communities if c.level == level or (c.level < level and c.is_leaf)]


def summary(communities: list[Community]) -> dict:
    levels: dict[int, list[Community]] = defaultdict(list)
    for c in communities:
        levels[c.level].append(c)
    return {
        "communities": len(communities),
        "by_level": {
            lvl: {
                "count": len(cs),
                "largest": max(c.size for c in cs),
                "stubs": sum(1 for c in cs if c.is_stub),
            }
            for lvl, cs in sorted(levels.items())
        },
        "leaves": sum(1 for c in communities if c.is_leaf),
        "stubs": sum(1 for c in communities if c.is_stub),
    }


def read_entity_graph(driver, index_version: str, database: str = "neo4j"):
    """(entities, weighted edges) for one index version. An edge weighs what its relations weigh."""
    with driver.session(database=database) as session:
        entities = [
            dict(r)
            for r in session.run(
                "MATCH (e:Entity {index_version: $v}) RETURN e.id AS id, e.name AS name,"
                " e.type AS type, e.description AS description ORDER BY e.id",
                v=index_version,
            )
        ]  # fmt: skip
        edges = [
            (r["a"], r["b"], float(r["w"] or 0))
            for r in session.run(
                "MATCH (a:Entity)-[r]->(b:Entity) WHERE r.index_version = $v"
                " RETURN a.id AS a, b.id AS b, r.weight AS w",
                v=index_version,
            )
        ]  # fmt: skip
    return entities, edges


def write_communities(
    driver,
    communities: list[Community],
    index_version: str,
    seed: int,
    max_cluster_size: int,
    database: str = "neo4j",
) -> None:
    """Idempotent: same input, same graph. Reports already on a surviving community are kept."""
    rows = [
        {
            "id": c.id, "level": c.level, "size": c.size, "is_leaf": c.is_leaf,
            "is_stub": c.is_stub, "parent_id": c.parent_id,
        }
        for c in communities
    ]  # fmt: skip
    memberships = [
        {"community": c.id, "entity": entity, "level": c.level}
        for c in communities
        for entity in c.members
    ]
    with driver.session(database=database) as session:
        for start in range(0, len(rows), BATCH):
            session.run(
                "UNWIND $rows AS row MERGE (c:Community {id: row.id})"
                " SET c.level = row.level, c.size = row.size, c.is_leaf = row.is_leaf,"
                " c.is_stub = row.is_stub, c.index_version = $version, c.seed = $seed,"
                " c.max_cluster_size = $max_size",
                rows=rows[start : start + BATCH], version=index_version, seed=seed,
                max_size=max_cluster_size,
            ).consume()  # fmt: skip
        # links are rebuilt every time, so an entity that moved never keeps its old community
        session.run(
            "MATCH (:Entity {index_version: $v})-[m:IN_COMMUNITY]->() DELETE m", v=index_version
        ).consume()
        session.run(
            "MATCH (:Community {index_version: $v})-[m:CHILD_OF]->() DELETE m", v=index_version
        ).consume()
        for start in range(0, len(memberships), BATCH):
            session.run(
                "UNWIND $rows AS row MATCH (e:Entity {id: row.entity})"
                " MATCH (c:Community {id: row.community})"
                " MERGE (e)-[m:IN_COMMUNITY {level: row.level}]->(c)",
                rows=memberships[start : start + BATCH],
            ).consume()
        session.run(
            "UNWIND $rows AS row WITH row WHERE row.parent_id IS NOT NULL"
            " MATCH (c:Community {id: row.id}) MATCH (p:Community {id: row.parent_id})"
            " MERGE (c)-[:CHILD_OF]->(p)",
            rows=rows,
        ).consume()
        session.run(
            "MATCH (c:Community {index_version: $v}) WHERE NOT c.id IN $ids DETACH DELETE c",
            v=index_version, ids=[c.id for c in communities],
        ).consume()  # fmt: skip


def read_communities(driver, index_version: str, database: str = "neo4j") -> list[Community]:
    """What is stored in Neo4j, rebuilt as Community objects (used to check the write)."""
    with driver.session(database=database) as session:
        rows = list(
            session.run(
                "MATCH (c:Community {index_version: $v})"
                " OPTIONAL MATCH (c)-[:CHILD_OF]->(p:Community)"
                " OPTIONAL MATCH (e:Entity)-[:IN_COMMUNITY]->(c)"
                " RETURN c.id AS id, c.level AS level, p.id AS parent,"
                " collect(e.id) AS members ORDER BY c.level, c.id",
                v=index_version,
            )
        )  # fmt: skip
    found = [Community(r["id"], r["level"], sorted(r["members"]), r["parent"]) for r in rows]
    by_id = {c.id: c for c in found}
    for c in found:
        if c.parent_id in by_id:
            by_id[c.parent_id].children.append(c.id)
    for c in found:
        c.children.sort()
    return found
