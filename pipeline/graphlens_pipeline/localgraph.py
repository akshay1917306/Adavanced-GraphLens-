"""Step 2 of local search: grow a small subgraph around the seeds and keep the best nodes.

1. Expand: one fixed, parameterised Cypher query follows the relation types of the ontology
   (never the community links) up to `max_hops` from the seeds and returns at most 200 entities.
   Relation types and the hop count are placed into the query text only after they are checked
   against the ontology and a short list; the question never reaches the query text.
2. Score: personalized PageRank (numpy) from the seeds over that candidate graph, blended with how
   close each entity is to the question (cosine of the embeddings). The best 60 are kept, and
   the seeds always stay.

No model is called. The result is deterministic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from graphlens_pipeline.graphstore import GraphLoadError, _checked
from graphlens_pipeline.linking import Linked

MAX_HOPS = 2
ALLOWED_HOPS = (1, 2, 3)
MAX_CANDIDATES = 200
KEEP_NODES = 60
DAMPING = 0.85
PPR_SHARE = 0.6  # the rest of the score is similarity to the question


@dataclass
class Node:
    id: str
    name: str
    type: str
    description: str
    sources: list[str]
    mentions: int
    hops: int  # 0 for a seed
    is_seed: bool = False
    ppr: float = 0.0
    similarity: float = 0.0
    score: float = 0.0


@dataclass
class Edge:
    source: str
    target: str
    predicate: str
    description: str
    weight: float
    evidence: list[str]


@dataclass
class Subgraph:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    candidates: int = 0  # how many entities the expansion found before scoring

    def unit_ids(self) -> set[str]:
        return {u for n in self.nodes for u in n.sources} | {
            u for e in self.edges for u in e.evidence
        }


def build_expand_query(predicates: list[str], max_hops: int) -> str:
    """The expansion query. Both parts placed into the text are checked first."""
    if max_hops not in ALLOWED_HOPS:
        raise GraphLoadError(f"max_hops must be one of {ALLOWED_HOPS}")
    kinds = "|".join(_checked(p, predicates) for p in predicates)
    return (
        "MATCH (s:Entity {index_version: $v}) WHERE s.id IN $seeds "
        f"MATCH p = (s)-[:{kinds}*1..{max_hops}]-(n:Entity {{index_version: $v}}) "
        "WHERE NOT n.id IN $seeds "
        "WITH n, min(length(p)) AS hops "
        "RETURN n.id AS id, hops ORDER BY hops, n.mention_count DESC, n.id LIMIT $limit"
    )


def expand(
    driver,
    seed_ids: list[str],
    predicates: list[str],
    index_version: str,
    max_hops: int = MAX_HOPS,
    limit: int = MAX_CANDIDATES,
    database: str = "neo4j",
) -> dict[str, int]:
    """{entity id: hops from the nearest seed} for the seeds (0) and what they reach."""
    if not seed_ids:
        return {}
    query = build_expand_query(predicates, max_hops)
    with driver.session(database=database) as session:
        rows = session.run(query, v=index_version, seeds=seed_ids, limit=limit)
        found = {r["id"]: r["hops"] for r in rows}
    return {**dict.fromkeys(seed_ids, 0), **found}


def fetch_nodes(driver, hops: dict[str, int], seeds: set[str], database: str = "neo4j"):
    """Node details and embeddings for the candidates."""
    with driver.session(database=database) as session:
        rows = list(
            session.run(
                "MATCH (e:Entity) WHERE e.id IN $ids RETURN e.id AS id, e.name AS name,"
                " e.type AS type, e.description AS description, e.source_unit_ids AS sources,"
                " e.mention_count AS mentions, e.embedding AS embedding",
                ids=list(hops),
            )
        )
    nodes = [
        Node(
            r["id"], r["name"], r["type"], r["description"] or "", list(r["sources"] or []),
            r["mentions"] or 0, hops[r["id"]], r["id"] in seeds,
        )
        for r in rows
    ]  # fmt: skip
    vectors = {r["id"]: r["embedding"] for r in rows if r["embedding"] is not None}
    return sorted(nodes, key=lambda n: n.id), vectors


def fetch_edges(
    driver, ids: list[str], predicates: list[str], index_version: str, database: str = "neo4j"
) -> list[Edge]:
    with driver.session(database=database) as session:
        rows = session.run(
            "MATCH (a:Entity {index_version: $v})-[r]->(b:Entity {index_version: $v})"
            " WHERE a.id IN $ids AND b.id IN $ids AND type(r) IN $predicates"
            " RETURN a.id AS a, b.id AS b, type(r) AS predicate, r.description AS description,"
            " r.weight AS weight, r.evidence_unit_ids AS evidence ORDER BY a.id, b.id, predicate",
            v=index_version, ids=ids, predicates=predicates,
        )  # fmt: skip
        return [
            Edge(r["a"], r["b"], r["predicate"], r["description"] or "", float(r["weight"] or 1.0),
                 list(r["evidence"] or []))
            for r in rows
        ]  # fmt: skip


def personalized_pagerank(
    ids: list[str],
    edges: list[tuple[str, str, float]],
    restart: dict[str, float],
    damping: float = DAMPING,
    iterations: int = 100,
    tolerance: float = 1e-10,
) -> dict[str, float]:
    """PageRank that jumps back to the restart nodes (the seeds), over an undirected graph.

    A node with no link passes its share back to the restart nodes. The scores add up to 1."""
    n = len(ids)
    if n == 0:
        return {}
    position = {node: i for i, node in enumerate(ids)}
    matrix = np.zeros((n, n))
    for a, b, weight in edges:
        if a in position and b in position and a != b and weight > 0:
            matrix[position[a], position[b]] += weight
            matrix[position[b], position[a]] += weight
    start = np.array([max(restart.get(node, 0.0), 0.0) for node in ids])
    start = start / start.sum() if start.sum() > 0 else np.full(n, 1.0 / n)
    column = matrix.sum(axis=0)
    dangling = column == 0
    transition = np.divide(matrix, column, out=np.zeros_like(matrix), where=~dangling)
    rank = start.copy()
    for _ in range(iterations):
        spread = damping * (transition @ rank + start * rank[dangling].sum())
        updated = spread + (1 - damping) * start
        if np.abs(updated - rank).sum() < tolerance:
            rank = updated
            break
        rank = updated
    return {node: float(rank[position[node]]) for node in ids}


def _unit(values: dict[str, float]) -> dict[str, float]:
    """Scale to 0..1 so two different measures can be blended."""
    if not values:
        return {}
    low, high = min(values.values()), max(values.values())
    span = high - low
    return {k: (v - low) / span if span > 0 else 0.0 for k, v in values.items()}


def cosine(a: list[float], b: list[float]) -> float:
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    norm = float(np.linalg.norm(x) * np.linalg.norm(y))
    return float(x @ y) / norm if norm else 0.0


def score_nodes(
    nodes: list[Node],
    edges: list[Edge],
    vectors: dict[str, list[float]],
    question_vector: list[float],
    seed_weights: dict[str, float],
    keep: int = KEEP_NODES,
    ppr_share: float = PPR_SHARE,
) -> list[Node]:
    """Blend PageRank and similarity to the question; keep the best `keep` and every seed."""
    ids = [n.id for n in nodes]
    ppr = personalized_pagerank(ids, [(e.source, e.target, e.weight) for e in edges], seed_weights)
    similarity = {
        n.id: cosine(vectors[n.id], question_vector) if n.id in vectors else 0.0 for n in nodes
    }
    ppr_unit, sim_unit = _unit(ppr), _unit(similarity)
    for node in nodes:
        node.ppr = ppr[node.id]
        node.similarity = similarity[node.id]
        node.score = ppr_share * ppr_unit[node.id] + (1 - ppr_share) * sim_unit[node.id]
    ranked = sorted(nodes, key=lambda n: (not n.is_seed, -n.score, n.id))
    seeds = [n for n in ranked if n.is_seed]
    rest = [n for n in ranked if not n.is_seed][: max(keep - len(seeds), 0)]
    return sorted(seeds + rest, key=lambda n: (not n.is_seed, -n.score, n.id))


def build_subgraph(
    driver,
    seeds: list[Linked],
    question_vector: list[float],
    predicates: list[str],
    index_version: str,
    max_hops: int = MAX_HOPS,
    keep: int = KEEP_NODES,
    use_pagerank: bool = True,
) -> Subgraph:
    """Expand from the seeds, score, keep the best nodes and the edges among them.

    With `use_pagerank=False` only similarity to the question ranks the nodes (used to measure
    what PageRank adds)."""
    seed_weights = {s.id: s.weight for s in seeds}
    hops = expand(driver, list(seed_weights), predicates, index_version, max_hops)
    if not hops:
        return Subgraph()
    nodes, vectors = fetch_nodes(driver, hops, set(seed_weights))
    edges = fetch_edges(driver, [n.id for n in nodes], predicates, index_version)
    chosen = score_nodes(
        nodes, edges, vectors, question_vector, seed_weights, keep,
        PPR_SHARE if use_pagerank else 0.0,
    )  # fmt: skip
    keep_ids = {n.id for n in chosen}
    kept_edges = [e for e in edges if e.source in keep_ids and e.target in keep_ids]
    return Subgraph(chosen, kept_edges, candidates=len(nodes))


def evidence_coverage(subgraph: Subgraph, wanted_units: set[str]) -> float:
    """Share of the wanted text units that the subgraph points at (a free measure of recall)."""
    if not wanted_units:
        return math.nan
    return len(wanted_units & subgraph.unit_ids()) / len(wanted_units)


def seeds_only_subgraph(driver, seeds: list[Linked]) -> Subgraph:
    """The seeds alone, no expansion (the first rung of the ablation)."""
    if not seeds:
        return Subgraph()
    nodes, _ = fetch_nodes(driver, dict.fromkeys((s.id for s in seeds), 0), {s.id for s in seeds})
    return Subgraph(nodes, [], candidates=len(nodes))
