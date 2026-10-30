"""Step 3 of local search: turn the subgraph into one budgeted context for the answer.

The context has three parts, each with its own share of the 8,000-token budget (the last 10%
is left empty on purpose):
- text units (45%): the passages that most of the chosen entities and edges point at, ranked by
  how many of them cite the passage and how close it is to the question; labelled [T1], [T2]...
- entities and relationships (25%): the best entities with their descriptions and the relations
  among them; entities are labelled [E1]...
- community reports (20%): the reports of the communities the seeds belong to (top 3); [C1]...

Everything that comes from the graph or the papers is untrusted text: it sits between tags and
angle brackets are neutralised. Nothing here calls a model.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import Engine, text

from graphlens_pipeline.linking import Linked
from graphlens_pipeline.localgraph import Subgraph, cosine
from graphlens_pipeline.reports import _clean

TOTAL_TOKENS = 8000
SHARES = {"units": 0.60, "entities": 0.25, "reports": 0.05}  # the other 10% is reserved
MAX_UNIT_TOKENS = 300
MAX_UNIT_CANDIDATES = 300
CITATION_WEIGHT = (
    0.25  # how much "cited by many entities" counts against closeness (tuned on the easy questions)
)
TOP_REPORTS = 3
REPORT_LEVEL = 1
MAX_ENTITY_DESCRIPTION = 220
MAX_RELATION_DESCRIPTION = 160
NL = chr(10)


@dataclass
class ContextItem:
    label: str  # T1, E3, C2
    kind: str  # unit, entity or community
    ref: str  # unit id, entity id or community id
    text: str
    tokens: int


@dataclass
class LocalContext:
    question: str
    items: list[ContextItem] = field(default_factory=list)
    prompt: str = ""
    tokens: dict[str, int] = field(default_factory=dict)
    left_out: dict[str, int] = field(default_factory=dict)  # candidates that did not fit
    graph: object = None  # the Subgraph it was built from (for the evidence graph on screen)

    def by_label(self) -> dict[str, ContextItem]:
        return {item.label: item for item in self.items}

    @property
    def total_tokens(self) -> int:
        return sum(self.tokens.values())


def _safe(value: str) -> str:
    """Text for a prompt that keeps its line breaks but cannot close a tag."""
    return value.replace("<", "(").replace(">", ")")


def _unit(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    low, high = min(values.values()), max(values.values())
    span = high - low
    return {k: (v - low) / span if span > 0 else 0.0 for k, v in values.items()}


# --- text units -------------------------------------------------------------------------------


def candidate_units(subgraph: Subgraph, limit: int = MAX_UNIT_CANDIDATES) -> Counter:
    """How many chosen entities and edges cite each text unit (the most cited first)."""
    cited: Counter = Counter()
    for node in subgraph.nodes:
        cited.update(set(node.sources))
    for edge in subgraph.edges:
        cited.update(set(edge.evidence))
    return Counter(dict(sorted(cited.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]))


def rank_units(
    cited: Counter, similarity: dict[str, float], citation_weight: float = CITATION_WEIGHT
) -> list[str]:
    """Best first: how often the entities cite the unit, against how close it is to the question."""
    cites = _unit({u: float(c) for u, c in cited.items()})
    close = _unit({u: similarity.get(u, 0.0) for u in cited})
    score = {u: citation_weight * cites[u] + (1 - citation_weight) * close[u] for u in cited}
    return sorted(cited, key=lambda u: (-score[u], u))


def postgres_unit_rows(engine: Engine, unit_ids: list[str]) -> dict[str, dict]:
    """Text, paper and section of each unit (the text lives in Postgres)."""
    if not unit_ids:
        return {}
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT u.id, u.text, d.title, d.metadata->>'paper_id' AS paper_id,"
                " d.metadata->'unit_sections'->>u.ordinal AS section"
                " FROM text_units u JOIN documents d ON d.id = u.document_id"
                " WHERE u.id = ANY(:ids)"
            ),
            {"ids": unit_ids},
        ).all()
    return {
        r.id: {
            "text": r.text, "title": r.title or "", "paper_id": r.paper_id or "",
            "section": r.section or "",
        }
        for r in rows
    }  # fmt: skip


def qdrant_unit_vectors(client, unit_ids: list[str], collection: str) -> dict[str, list[float]]:
    """The dense vector of each unit, read back from Qdrant."""
    from graphlens_pipeline.embed import point_id

    if not unit_ids:
        return {}
    by_point = {point_id(u): u for u in unit_ids}
    points = client.retrieve(
        collection, ids=list(by_point), with_payload=False, with_vectors=["dense"]
    )
    return {by_point[str(p.id)]: list(p.vector["dense"]) for p in points if p.vector}


# --- the other two parts ----------------------------------------------------------------------


def seed_reports(
    driver,
    seeds: list[Linked],
    index_version: str,
    level: int = REPORT_LEVEL,
    top: int = TOP_REPORTS,
    database: str = "neo4j",
) -> list[dict]:
    """Reports of the communities the seeds belong to: most seeds first, then the rating."""
    if not seeds:
        return []
    with driver.session(database=database) as session:
        rows = session.run(
            "MATCH (e:Entity)-[:IN_COMMUNITY]->(c:Community)"
            " WHERE e.id IN $ids AND c.index_version = $v AND c.is_stub = false"
            " AND c.report_title IS NOT NULL"
            " AND (c.level = $level OR (c.level < $level AND c.is_leaf))"
            " RETURN c.id AS id, c.report_title AS title, c.report_summary AS summary,"
            " c.report_findings AS findings, c.report_rating AS rating,"
            " count(DISTINCT e) AS seeds ORDER BY seeds DESC, rating DESC, id LIMIT $top",
            ids=[s.id for s in seeds], v=index_version, level=level, top=top,
        )  # fmt: skip
        return [dict(r) for r in rows]


# --- assembly ---------------------------------------------------------------------------------


def _fit(blocks: list[tuple[str, str, str]], budget: int, count) -> tuple[list, int, int]:
    """Keep blocks in order while they fit. Returns (kept, tokens used, how many were left out)."""
    kept, used = [], 0
    for kind, ref, body in blocks:
        size = count(body)
        if size > budget or (kept and used + size > budget):
            continue  # a smaller block further down may still fit
        kept.append((kind, ref, body, size))
        used += size
    return kept, used, len(blocks) - len(kept)


def assemble(
    question: str,
    subgraph: Subgraph,
    rows: dict[str, dict],
    similarity: dict[str, float],
    reports: list[dict],
    count,
    total_tokens: int = TOTAL_TOKENS,
    citation_weight: float = CITATION_WEIGHT,
    priority_units: tuple[str, ...] = (),
) -> LocalContext:
    """Build the labelled, budgeted context. `rows` are the text units fetched from Postgres,
    `similarity` the cosine of each to the question, `count` a token counter."""
    ctx = LocalContext(question)
    budgets = {k: int(total_tokens * v) for k, v in SHARES.items()}

    # entities: the best nodes with their descriptions, then the relations among those shown
    nodes = sorted(subgraph.nodes, key=lambda n: (not n.is_seed, -n.score, n.id))
    entity_blocks = [
        (
            "entity",
            n.id,
            f"{_clean(n.name, 100)} ({n.type}): {_clean(n.description, MAX_ENTITY_DESCRIPTION)}",
        )
        for n in nodes
    ]
    entity_budget = int(budgets["entities"] * 0.7)
    kept_entities, used_entities, dropped = _fit(entity_blocks, entity_budget, count)
    label_of = {ref: f"E{i}" for i, (_, ref, _, _) in enumerate(kept_entities, start=1)}
    relation_blocks = []
    for edge in sorted(subgraph.edges, key=lambda e: (-e.weight, e.source, e.target, e.predicate)):
        if edge.source in label_of and edge.target in label_of:
            body = (
                f"{label_of[edge.source]} {edge.predicate} {label_of[edge.target]}: "
                f"{_clean(edge.description, MAX_RELATION_DESCRIPTION)}"
            )
            ref = f"{edge.source}|{edge.predicate}|{edge.target}"
            relation_blocks.append(("relation", ref, body))
    kept_relations, used_relations, dropped_relations = _fit(
        relation_blocks, budgets["entities"] - used_entities, count
    )
    ctx.tokens["entities"] = used_entities + used_relations
    ctx.left_out["entities"], ctx.left_out["relationships"] = dropped, dropped_relations

    # text units, best first, each cut to at most 450 tokens
    unit_blocks = []
    ranked = rank_units(candidate_units(subgraph), similarity, citation_weight)
    # units that must come first (for example the best hits of a plain search), then the rest
    ordered = [u for u in priority_units if u in rows] + [
        u for u in ranked if u not in priority_units
    ]
    for unit_id in ordered:
        row = rows.get(unit_id)
        if not row:
            continue
        words = row["text"].split()
        while count(" ".join(words)) > MAX_UNIT_TOKENS and len(words) > 20:
            words = words[: int(len(words) * 0.9)]
        head = f"paper {row['paper_id']}, section {_clean(row['section'], 60) or 'none'}"
        unit_blocks.append(("unit", unit_id, head + NL + _safe(" ".join(words))))
    kept_units, used_units, dropped_units = _fit(unit_blocks, budgets["units"], count)
    ctx.tokens["units"], ctx.left_out["units"] = used_units, dropped_units

    # community reports
    report_blocks = []
    for report in reports:
        findings = sorted(
            json.loads(report["findings"] or "[]"), key=lambda f: -f.get("importance", 0)
        )
        lines = [_clean(report["title"], 120), _clean(report["summary"], 600)]
        lines += [f"- {_clean(f['summary'], 200)}" for f in findings[:3]]
        report_blocks.append(("community", report["id"], NL.join(lines)))
    kept_reports, used_reports, dropped_reports = _fit(report_blocks, budgets["reports"], count)
    ctx.tokens["reports"], ctx.left_out["reports"] = used_reports, dropped_reports

    # labels are given last, so every label points at a block that is really shown
    for i, (kind, ref, body, size) in enumerate(kept_units, start=1):
        ctx.items.append(ContextItem(f"T{i}", kind, ref, body, size))
    for i, (kind, ref, body, size) in enumerate(kept_entities, start=1):
        ctx.items.append(ContextItem(f"E{i}", kind, ref, body, size))
    for i, (kind, ref, body, size) in enumerate(kept_reports, start=1):
        ctx.items.append(ContextItem(f"C{i}", kind, ref, body, size))

    parts = []
    texts = [item for item in ctx.items if item.label[0] == "T"]
    if texts:
        body = (NL + NL).join(f"[{i.label}] {i.text}" for i in texts)
        parts.append("<texts>" + NL + body + NL + "</texts>")
    entities = [item for item in ctx.items if item.label[0] == "E"]
    if entities:
        lines = [f"[{i.label}] {i.text}" for i in entities] + [b for _, _, b, _ in kept_relations]
        parts.append("<graph>" + NL + NL.join(lines) + NL + "</graph>")
    communities = [item for item in ctx.items if item.label[0] == "C"]
    if communities:
        body = (NL + NL).join(f"[{i.label}] {i.text}" for i in communities)
        parts.append("<communities>" + NL + body + NL + "</communities>")
    ctx.prompt = (
        f"Question: {_clean(question, 400)}" + NL + "<context>" + NL + NL.join(parts) + NL
        + "</context>"
    )  # fmt: skip
    return ctx


def similarity_to_question(
    question_vector: list[float], vectors: dict[str, list[float]]
) -> dict[str, float]:
    return {unit: cosine(vector, question_vector) for unit, vector in vectors.items()}
