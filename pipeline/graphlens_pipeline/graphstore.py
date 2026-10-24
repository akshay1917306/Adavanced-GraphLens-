"""Load the resolved graph into Neo4j.

Safety rules for this module:
- Every query is a fixed template. Values always travel as parameters. The only things placed
  into query text are labels and relationship types, and those come from the ontology and are
  checked against `NAME` first. No model ever writes Cypher.
- Loading is idempotent: nodes and edges are MERGEd by stable keys, so running it twice gives the
  same graph, and anything an earlier load of the same index version wrote but this one did not
  is removed (only that version's own nodes and edges).
- Every entity must have source text units and every edge must have evidence text units, or the
  load refuses to start.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from graphlens_pipeline.ontology import Ontology
from graphlens_pipeline.resolve import Resolution

SCHEMA_DIR = Path(__file__).parent / "graph_schema"
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,40}")
BATCH = 500
EMBEDDING_DIMENSIONS = 768


class GraphLoadError(Exception):
    pass


@dataclass
class GraphCounts:
    entities: int
    entities_by_type: dict[str, int]
    relations: int
    relations_by_predicate: dict[str, int]
    with_embedding: int


def _checked(name: str, allowed: list[str]) -> str:
    """A label or relationship type that is safe to put into query text."""
    if name not in allowed or not NAME.fullmatch(name):
        raise GraphLoadError(f"{name!r} is not allowed by the ontology")
    return name


def schema_scripts() -> list[tuple[str, str, str]]:
    """(version, checksum, text) of every schema script, in order."""
    scripts = []
    for path in sorted(SCHEMA_DIR.glob("V*.cypher")):
        body = path.read_text(encoding="utf-8")
        scripts.append((path.stem, hashlib.sha256(body.encode()).hexdigest()[:16], body))
    return scripts


def _statements(body: str) -> list[str]:
    lines = [ln for ln in body.splitlines() if not ln.strip().startswith("//")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def apply_schema(driver, database: str = "neo4j") -> list[str]:
    """Run the schema scripts that have not run yet. Returns the versions applied now.

    A script that was already applied and has changed since is an error: schema changes go into
    a new numbered script.
    """
    applied_now = []
    with driver.session(database=database) as session:
        session.run(
            "CREATE CONSTRAINT schema_version IF NOT EXISTS"
            " FOR (s:SchemaVersion) REQUIRE s.version IS UNIQUE"
        ).consume()
        done = {
            r["version"]: r["checksum"]
            for r in session.run("MATCH (s:SchemaVersion) RETURN s.version AS version,"
                                 " s.checksum AS checksum")
        }  # fmt: skip
        for version, checksum, body in schema_scripts():
            if version in done:
                if done[version] != checksum:
                    raise GraphLoadError(f"{version} changed after it was applied")
                continue
            for statement in _statements(body):
                session.run(statement).consume()
            session.run(
                "MERGE (s:SchemaVersion {version: $v}) SET s.checksum = $c,"
                " s.applied_at = datetime()",
                v=version, c=checksum,
            ).consume()  # fmt: skip
            applied_now.append(version)
    return applied_now


def embedding_text(name: str, description: str) -> str:
    return f"{name}: {description}"[:400] if description else name


def check_provenance(resolution: Resolution) -> None:
    ids = {e.id for e in resolution.entities}
    for entity in resolution.entities:
        if not entity.source_unit_ids:
            raise GraphLoadError(f"entity {entity.name!r} has no source text unit")
    for relation in resolution.relations:
        if not relation.evidence_unit_ids:
            raise GraphLoadError(f"a {relation.predicate} edge has no evidence text unit")
        if relation.source_id not in ids or relation.target_id not in ids:
            raise GraphLoadError(f"a {relation.predicate} edge points to a missing entity")


def relation_key(source_id: str, predicate: str, target_id: str) -> str:
    return f"{source_id}|{predicate}|{target_id}"


def load_graph(
    driver,
    resolution: Resolution,
    ontology: Ontology,
    vectors: dict[str, list[float]],
    index_version: str,
    database: str = "neo4j",
) -> GraphCounts:
    """Write entities and relations. `vectors` maps entity id to its embedding."""
    check_provenance(resolution)
    for entity in resolution.entities:
        if len(vectors.get(entity.id, [])) != EMBEDDING_DIMENSIONS:
            raise GraphLoadError(f"entity {entity.name!r} has no {EMBEDDING_DIMENSIONS}-d vector")
    rows = [
        {
            "id": e.id, "name": e.name, "type": e.type, "description": e.description,
            "aliases": e.aliases, "aliases_text": " | ".join(e.aliases),
            "mention_count": e.mention_count, "source_unit_ids": e.source_unit_ids,
            "embedding": vectors[e.id],
        }
        for e in resolution.entities
    ]  # fmt: skip
    with driver.session(database=database) as session:
        for start in range(0, len(rows), BATCH):
            session.run(
                "UNWIND $rows AS row MERGE (e:Entity {id: row.id})"
                " SET e.name = row.name, e.type = row.type, e.description = row.description,"
                " e.aliases = row.aliases, e.aliases_text = row.aliases_text,"
                " e.mention_count = row.mention_count, e.source_unit_ids = row.source_unit_ids,"
                " e.index_version = $version"
                " WITH e, row CALL db.create.setNodeVectorProperty(e, 'embedding', row.embedding)",
                rows=rows[start : start + BATCH], version=index_version,
            ).consume()  # fmt: skip
        for type_name in ontology.type_names:
            label = _checked(type_name, ontology.type_names)
            session.run(
                f"MATCH (e:Entity {{index_version: $version, type: $type}}) SET e:{label}",
                version=index_version, type=type_name,
            ).consume()  # fmt: skip
        keys = []
        for predicate in ontology.predicate_names:
            name = _checked(predicate, ontology.predicate_names)
            edges = [
                {
                    "key": relation_key(r.source_id, r.predicate, r.target_id),
                    "source": r.source_id, "target": r.target_id,
                    "description": r.description, "weight": r.weight,
                    "confidence": r.confidence, "evidence_unit_ids": r.evidence_unit_ids,
                }
                for r in resolution.relations
                if r.predicate == predicate
            ]  # fmt: skip
            keys += [e["key"] for e in edges]
            for start in range(0, len(edges), BATCH):
                session.run(
                    "UNWIND $rows AS row"
                    " MATCH (a:Entity {id: row.source}) MATCH (b:Entity {id: row.target})"
                    f" MERGE (a)-[r:{name} {{key: row.key}}]->(b)"
                    " SET r.description = row.description, r.weight = row.weight,"
                    " r.confidence = row.confidence, r.evidence_unit_ids = row.evidence_unit_ids,"
                    " r.index_version = $version",
                    rows=edges[start : start + BATCH], version=index_version,
                ).consume()  # fmt: skip
        # what an earlier load of this same version wrote and this one did not
        session.run(
            "MATCH ()-[r]->() WHERE r.index_version = $version AND NOT r.key IN $keys DELETE r",
            version=index_version, keys=keys,
        ).consume()  # fmt: skip
        session.run(
            "MATCH (e:Entity {index_version: $version}) WHERE NOT e.id IN $ids DETACH DELETE e",
            version=index_version, ids=[e.id for e in resolution.entities],
        ).consume()  # fmt: skip
    return count_graph(driver, index_version, database)


def count_graph(driver, index_version: str, database: str = "neo4j") -> GraphCounts:
    with driver.session(database=database) as session:
        by_type = {
            r["type"]: r["n"]
            for r in session.run(
                "MATCH (e:Entity {index_version: $v}) RETURN e.type AS type, count(*) AS n",
                v=index_version,
            )
        }
        by_predicate = {
            r["predicate"]: r["n"]
            for r in session.run(
                "MATCH ()-[r]->() WHERE r.index_version = $v"
                " RETURN type(r) AS predicate, count(*) AS n",
                v=index_version,
            )
        }
        embedded = session.run(
            "MATCH (e:Entity {index_version: $v}) WHERE e.embedding IS NOT NULL"
            " RETURN count(*) AS n",
            v=index_version,
        ).single()["n"]
    return GraphCounts(
        entities=sum(by_type.values()), entities_by_type=by_type,
        relations=sum(by_predicate.values()), relations_by_predicate=by_predicate,
        with_embedding=embedded,
    )  # fmt: skip
