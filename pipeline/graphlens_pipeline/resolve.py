"""Entity resolution: decide which extracted mentions are the same real thing.

Each paper unit gives many mentions ("graph neural network", "Graph Neural Networks (GNNs)",
"GNN"). We group them into one entity per real thing, keeping every spelling as an alias, and
move the relations onto the merged entities. A wrong merge is worse than a missed one (two
different methods fused break multi-hop answers), so the rules are conservative:

1. Exact grouping: names that differ only by case, punctuation, spaces, hyphens or a plural "s"
   ("multi-hop", "multihop", "Multi hop") are merged without asking anyone.
2. Acronyms written next to their long form, "Graph Neural Networks (GNNs)", link the acronym to
   that long form wherever it appears alone.
3. The current paper is recognised by its own title (the model often shortens it).
4. For the rest, candidate pairs of the same type are found by spelling similarity, shared
   acronyms and name embeddings. A pair whose numbers or size words differ ("T5 base" and
   "T5 large", "GPT-3" and "GPT-4") is never merged. Very close pairs merge automatically; the
   gray zone is sent to a language model, which must answer "same" only when it is clearly the
   same thing; the model's answers are cached and the spend is capped.

Every pair that was scored is stored with its score, method and reason (`resolution_decisions`).
"""

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from sqlalchemy import Engine, text

from graphlens_pipeline.extract import UnitResult
from graphlens_pipeline.llm import Llm, LlmError, cost_usd
from graphlens_pipeline.ontology import Ontology

AUTO_MERGE_SCORE = 0.95
ASK_MODEL_SCORE = 0.80
EMBEDDING_THRESHOLD = 0.88
MAX_EVIDENCE_PER_EDGE = 20
GENERIC_TAILS = {
    "model", "models", "method", "methods", "approach", "framework", "system", "systems",
    "dataset", "datasets", "benchmark", "baseline", "baselines", "network", "networks", "module",
}  # fmt: skip
SIZE_WORDS = {"base", "large", "small", "tiny", "mini", "xl", "xxl", "medium", "huge", "nano"}
NEGATIONS = {"no", "without", "wo", "non", "not"}
PARENTHESIS = re.compile(r"\(([^()]{1,30})\)")
JUDGE_PROMPT_VERSION = "resolve-v2"  # v2: stricter "same" rules after a check of the v1 merges
EMPTY_WORDS = {
    "the", "a", "an", "task", "tasks", "model", "models", "method", "methods", "dataset",
    "datasets", "approach", "framework", "system", "systems", "setting", "problem",
}  # fmt: skip
JUDGE_SYSTEM = """You decide whether two names from research papers refer to exactly the same \
real thing (the same method, dataset, task, author or organization).

Answer with JSON only: {"same": true or false, "reason": "<one short sentence>"}

Say true ONLY for: an abbreviation and its full name, two spellings of one name, a plural or a \
different word order of the same name, or the same name with a harmless extra word such as \
"model", "task" or "dataset".

Say false for everything else, especially:
- one name is broader or narrower than the other ("link prediction" and "KG link prediction", \
"reasoning" and "multi-hop reasoning");
- two similar-looking names of different datasets, methods or people (for example "TempQuestions" \
and "TimeQuestions");
- a name stuck to a symbol or variable ("Lretrieval" and "retrieval");
- a thing and one of its parts, a task and a dataset made for it, or question answering and \
reading comprehension;
- a name made only of generic words ("task", "the task").
When unsure, say false. A wrong merge is much worse than a missed one."""
JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["same", "reason"],
    "properties": {"same": {"type": "boolean"}, "reason": {"type": "string"}},
}


def squash_name(name: str) -> str:
    """Letters and digits only, lower case, no plural "s": the key for exact grouping."""
    text_ = unicodedata.normalize("NFKC", PARENTHESIS.sub(" ", name)).casefold()
    key = re.sub(r"[^0-9a-z]+", "", text_)
    return key[:-1] if len(key) > 3 and key.endswith("s") and not key.endswith("ss") else key


def tokens(name: str) -> list[str]:
    text_ = unicodedata.normalize("NFKC", PARENTHESIS.sub(" ", name)).casefold()
    return re.sub(r"[^0-9a-z]+", " ", text_).split()


def parenthetical_acronym(name: str) -> str | None:
    """ "Graph Neural Networks (GNNs)" -> "GNNs". Only short, letter-like contents count."""
    match = PARENTHESIS.search(name)
    if not match:
        return None
    inside = match.group(1).strip()
    if 2 <= len(inside) <= 10 and re.fullmatch(r"[A-Za-z][A-Za-z0-9\-]*", inside):
        return inside
    return None


def initials(name: str) -> str:
    return "".join(t[0] for t in tokens(name) if t not in {"of", "the", "and", "for", "a", "an"})


@dataclass
class Cluster:
    key: str  # the squashed name this cluster started from
    type: str
    surface: Counter = field(default_factory=Counter)  # spelling -> mentions
    descriptions: Counter = field(default_factory=Counter)
    units: set = field(default_factory=set)
    mentions: int = 0

    @property
    def name(self) -> str:
        """The most used spelling; ties go to the longer one."""
        return max(self.surface, key=lambda s: (self.surface[s], len(s)))

    @property
    def id(self) -> str:
        return "e_" + hashlib.sha1(f"{self.type}|{self.key}".encode()).hexdigest()[:12]  # noqa: S324


@dataclass(frozen=True)
class Decision:
    a: str  # "Type:name" of the first cluster
    b: str
    score: float
    method: str  # auto_merge, llm or rejected (the values the database allows)
    decision: str  # merge or keep_separate
    rationale: str


@dataclass
class ResolvedEntity:
    id: str
    name: str
    type: str
    aliases: list[str]
    description: str
    mention_count: int
    source_unit_ids: list[str]


@dataclass
class ResolvedRelation:
    source_id: str
    predicate: str
    target_id: str
    description: str
    weight: float
    confidence: float
    evidence_unit_ids: list[str]


@dataclass
class Resolution:
    entities: list[ResolvedEntity]
    relations: list[ResolvedRelation]
    decisions: list[Decision]
    mentions: int = 0
    clusters_before_merging_pairs: int = 0
    dropped_noise: int = 0
    model_cost_usd: float = 0.0
    model_calls: int = 0
    unasked_pairs: int = 0  # gray-zone pairs left separate because the cost cap was reached


class _Union:
    def __init__(self, keys):
        self.parent = {k: k for k in keys}

    def find(self, k):
        while self.parent[k] != k:
            self.parent[k] = self.parent[self.parent[k]]
            k = self.parent[k]
        return k

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)  # the smaller key stays the root: stable ids


def is_noise(name: str) -> bool:
    """Table headers and symbols such as "q", "hp" or "r1" are not entities worth keeping."""
    compact = re.sub(r"[^0-9a-z]+", "", name.casefold())
    only_empty_words = bool(tokens(name)) and set(tokens(name)) <= EMPTY_WORDS
    return len(compact) < 2 or compact.isdigit() or only_empty_words


def blocked_by_rules(a: str, b: str) -> str | None:
    """A reason why two names must never be merged, or None."""
    ta, tb = tokens(a), tokens(b)
    if {t for t in ta if t.isdigit()} != {t for t in tb if t.isdigit()}:
        return "different numbers"
    if (set(ta) & SIZE_WORDS) != (set(tb) & SIZE_WORDS):
        return "different size or version word"
    if (set(ta) & NEGATIONS) != (set(tb) & NEGATIONS):
        return "one name is a negation"
    return None


def spelling_score(a: str, b: str) -> tuple[float, bool]:
    """(0 to 1 alikeness, safe to merge without asking).

    Only one case is safe: one name is the other plus a generic word ("KG-FiD" and "KG-FiD
    model"). Everything else that merely looks similar goes to the model, even a one-character
    difference, because "Adam" and "AdamW" or "NQ reading comprehension task" and "reading
    comprehension task" look alike but are different things.
    """
    from difflib import SequenceMatcher

    ka, kb = squash_name(a), squash_name(b)
    matcher = SequenceMatcher(None, ka, kb)
    # quick_ratio is a cheap upper bound; skip the slow exact ratio when it cannot reach the bar
    score = matcher.ratio() if matcher.quick_ratio() >= ASK_MODEL_SCORE else 0.0
    safe = False
    ta, tb = tokens(a), tokens(b)
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if short and long_[: len(short)] == short and set(long_[len(short) :]) <= GENERIC_TAILS:
        score, safe = max(score, 0.96), True  # "KG-FiD" and "KG-FiD model"
    if short and long_[-len(short) :] == short and set(long_[: -len(short)]) <= GENERIC_TAILS:
        score, safe = max(score, 0.96), True
    for x, y in ((a, b), (b, a)):
        letters = re.sub(r"[^0-9a-z]+", "", x.casefold())
        if 2 <= len(letters) <= 8 and len(tokens(y)) >= 2 and initials(y) == letters:
            score = max(score, 0.85)  # an acronym of the other name: ask, do not assume
    return round(score, 3), safe


def acronym_fits(acronym: str, long_name: str) -> bool:
    """The acronym's letters appear in order in the long name and start with its first letter."""
    letters = re.sub(r"[^0-9a-z]+", "", acronym.casefold())
    full = re.sub(r"[^0-9a-z]+", "", PARENTHESIS.sub(" ", long_name).casefold())
    if len(letters) < 2 or len(full) <= len(letters) or letters[0] != full[0]:
        return False
    position = 0
    for letter in letters:
        position = full.find(letter, position)
        if position < 0:
            return False
        position += 1
    return True


def build_clusters(
    results: dict[str, UnitResult], paper_titles: dict[str, str]
) -> tuple[dict[tuple[str, str], Cluster], int, int]:
    """Group mentions by (type, squashed name). Returns (clusters, mentions, noise dropped)."""
    clusters: dict[tuple[str, str], Cluster] = {}
    mentions = noise = 0
    for unit_id, result in results.items():
        own_title = paper_titles.get(unit_id, "")
        for entity in result.entities:
            mentions += 1
            name = entity.name
            if entity.type == "Paper" and own_title:
                name = _own_title_or(name, own_title)
            if is_noise(name):
                noise += 1
                continue
            key = (entity.type, squash_name(name))
            cluster = clusters.setdefault(key, Cluster(key=key[1], type=entity.type))
            cluster.surface[name] += 1
            if entity.description:
                cluster.descriptions[entity.description] += 1
            cluster.units.add(unit_id)
            cluster.mentions += 1
    return clusters, mentions, noise


def _own_title_or(name: str, title: str) -> str:
    """If the model wrote the current paper's title in a shortened form, use the real title."""
    from difflib import SequenceMatcher

    a, b = squash_name(name), squash_name(title)
    own, full = tokens(name), tokens(title)
    starts_the_title = len(own) >= 3 and full[: len(own)] == own  # a cut-off title
    if a and (starts_the_title or SequenceMatcher(None, a, b).ratio() >= 0.85):
        return title
    return name


def link_acronyms(
    results: dict[str, UnitResult], clusters: dict[tuple[str, str], Cluster], union: _Union
) -> list[Decision]:
    """ "Long Form (ACR)" in one mention says ACR is that long form; merge a lone ACR with it."""
    decisions: list[Decision] = []
    acr_to_long: dict[tuple[str, str], set[str]] = defaultdict(set)
    for result in results.values():
        for entity in result.entities:
            acr = parenthetical_acronym(entity.name)
            # only "Long Form (ACR)" with the bracket at the end, and an acronym that fits
            if acr and entity.name.rstrip().endswith(")") and acronym_fits(acr, entity.name):
                acr_to_long[(entity.type, squash_name(acr))].add(squash_name(entity.name))
    for (type_, acr_key), longs in acr_to_long.items():
        if len(longs) != 1:  # the same acronym explained two ways: leave it alone
            continue
        long_key = next(iter(longs))
        a, b = (type_, acr_key), (type_, long_key)
        if a in clusters and b in clusters and a != b:
            union.union(a, b)
            decisions.append(
                Decision(
                    f"{type_}:{clusters[a].name}",
                    f"{type_}:{clusters[b].name}",
                    1.0,
                    "auto_merge",
                    "merge",
                    "acronym written next to its long form",
                )  # fmt: skip
            )
    return decisions


def candidate_pairs(
    clusters: dict[tuple[str, str], Cluster],
    union: _Union,
    name_vectors: dict[tuple[str, str], list[float]],
) -> list[tuple[Cluster, Cluster, float, str]]:
    """Pairs of same-type clusters that look alike. Returns (a, b, score, why)."""
    import numpy as np

    by_type: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key in clusters:
        by_type[key[0]].append(key)
    pairs: dict[frozenset, tuple[float, str]] = {}
    for type_, keys in by_type.items():
        if type_ in {"Paper", "Author"}:
            continue  # papers go by their titles; people only merge when exactly equal
        names = [clusters[k].name for k in keys]
        for i, ka in enumerate(keys):
            for j in range(i + 1, len(keys)):
                kb = keys[j]
                if union.find(ka) == union.find(kb):
                    continue
                score, safe = spelling_score(names[i], names[j])
                if score >= ASK_MODEL_SCORE:
                    pairs[frozenset((ka, kb))] = (score, "spelling-safe" if safe else "spelling")
        matrix = np.array([name_vectors[k] for k in keys])
        sims = matrix @ matrix.T
        for i, j in zip(*np.where(np.triu(sims, 1) >= EMBEDDING_THRESHOLD), strict=True):
            ka, kb = keys[i], keys[j]
            if union.find(ka) != union.find(kb) and frozenset((ka, kb)) not in pairs:
                pairs[frozenset((ka, kb))] = (round(float(sims[i, j]) * 0.9, 3), "embedding")
    out = []
    for pair, (score, why) in pairs.items():
        a, b = sorted(pair)
        out.append((clusters[a], clusters[b], score, why))
    return sorted(out, key=lambda p: (-p[2], p[0].key, p[1].key))


def judge_pair(llm: Llm, a: Cluster, b: Cluster, engine: Engine | None) -> tuple[bool, str, float]:
    """Ask the model whether two names are the same thing. Returns (same, reason, cost).

    Answers are cached in the database; with `engine=None` nothing is cached (used in tests).
    """
    first, second = a.name, b.name
    cache = hashlib.sha256(
        f"{JUDGE_PROMPT_VERSION}|{llm.model}|{a.type}|{first}|{second}".encode()
    ).hexdigest()
    if engine is not None:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT result FROM extraction_cache WHERE cache_key = :k"), {"k": cache}
            ).first()
        if row:
            return row[0]["same"], row[0]["reason"], 0.0
    describe = lambda c: (c.descriptions.most_common(1) or [("", 0)])[0][0][:200]  # noqa: E731
    user = (
        f"Type: {a.type}\nName A: {first}\nA is described as: {describe(a)}\n"
        f"Name B: {second}\nB is described as: {describe(b)}"
    )
    reply = llm.complete(JUDGE_SYSTEM, user, 150, json_schema=JUDGE_SCHEMA)
    try:
        data = json.loads(reply.text)
        same, reason = bool(data["same"]), str(data.get("reason", ""))[:300]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise LlmError("judge answer not usable") from error
    cost = cost_usd(reply.model, reply.tokens_in, reply.tokens_out) or 0.0
    if engine is not None:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO extraction_cache (cache_key, result, tokens_in, tokens_out)"
                    " VALUES (:k, CAST(:r AS jsonb), :ti, :to) ON CONFLICT (cache_key) DO NOTHING"
                ),
                {"k": cache, "r": json.dumps({"same": same, "reason": reason}),
                 "ti": reply.tokens_in, "to": reply.tokens_out},
            )  # fmt: skip
    return same, reason, cost


def resolve(
    engine: Engine | None,
    results: dict[str, UnitResult],
    paper_titles: dict[str, str],
    ontology: Ontology,
    name_vectors_for,
    llm: Llm | None = None,
    max_cost_usd: float = 0.25,
) -> Resolution:
    """Group mentions into entities and move the relations onto them.

    `name_vectors_for(names)` returns one unit-length vector per name (local embeddings).
    With `llm=None` the gray zone is left unmerged.
    """
    clusters, mentions, noise = build_clusters(results, paper_titles)
    union = _Union(clusters)
    decisions = link_acronyms(results, clusters, union)

    keys = list(clusters)
    vectors = dict(zip(keys, name_vectors_for([clusters[k].name for k in keys]), strict=True))
    spent, calls, unasked = 0.0, 0, 0
    pairs = candidate_pairs(clusters, union, vectors)
    answers = _ask_in_parallel(llm, pairs, engine, max_cost_usd) if llm is not None else {}
    for a, b, score, why in pairs:
        label_a, label_b = f"{a.type}:{a.name}", f"{b.type}:{b.name}"
        blocked = blocked_by_rules(a.name, b.name)
        if blocked:
            decisions.append(
                Decision(label_a, label_b, score, "rejected", "keep_separate", blocked)
            )
        elif score >= AUTO_MERGE_SCORE and why == "spelling-safe":
            union.union((a.type, a.key), (b.type, b.key))
            decisions.append(
                Decision(label_a, label_b, score, "auto_merge", "merge", "near-identical spelling")
            )
        elif llm is None or (a.key, b.key, a.type) not in answers:
            unasked += 1
            decisions.append(
                Decision(
                    label_a, label_b, score, "rejected", "keep_separate", "gray zone not asked"
                )
            )
        else:
            outcome = answers[(a.key, b.key, a.type)]
            if outcome is None:
                unasked += 1
                decisions.append(
                    Decision(
                        label_a, label_b, score, "rejected", "keep_separate", "model call failed"
                    )
                )
                continue
            same, reason, cost = outcome
            spent += cost
            calls += 1 if cost else 0
            if same:
                union.union((a.type, a.key), (b.type, b.key))
            decisions.append(
                Decision(
                    label_a, label_b, score, "llm", "merge" if same else "keep_separate", reason
                )
            )

    merged = _merge_clusters(clusters, union)
    entities = [_entity(c) for c in merged.values()]
    relations = _relations(results, clusters, union, merged, ontology, paper_titles)
    return Resolution(
        entities=sorted(entities, key=lambda e: (e.type, e.name.casefold())),
        relations=relations, decisions=decisions, mentions=mentions,
        clusters_before_merging_pairs=len(clusters), dropped_noise=noise,
        model_cost_usd=round(spent, 6), model_calls=calls, unasked_pairs=unasked,
    )  # fmt: skip


def _ask_in_parallel(llm: Llm, pairs, engine: Engine | None, max_cost_usd: float, workers: int = 8):
    """Ask the model about every gray-zone pair, several at a time.

    The answer to one pair never depends on another, so the order does not matter. Returns
    {(key_a, key_b, type): (same, reason, cost)}, or None for a failed call. Stops asking
    (pairs missing from the result) once the spend reaches the cap.
    """
    todo = [
        (a, b)
        for a, b, score, why in pairs
        if not blocked_by_rules(a.name, b.name)
        and not (score >= AUTO_MERGE_SCORE and why == "spelling-safe")
    ]
    answers: dict = {}
    spent = 0.0

    def ask(pair):
        a, b = pair
        try:
            return (a.key, b.key, a.type), judge_pair(llm, a, b, engine)
        except LlmError:
            return (a.key, b.key, a.type), None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for start in range(0, len(todo), workers * 4):
            if spent >= max_cost_usd:
                break
            for key, outcome in pool.map(ask, todo[start : start + workers * 4]):
                answers[key] = outcome
                spent += outcome[2] if outcome else 0.0
    return answers


def _merge_clusters(
    clusters: dict[tuple[str, str], Cluster], union: _Union
) -> dict[tuple[str, str], Cluster]:
    merged: dict[tuple[str, str], Cluster] = {}
    for key, cluster in clusters.items():
        root = union.find(key)
        target = merged.setdefault(root, Cluster(key=root[1], type=root[0]))
        target.surface.update(cluster.surface)
        target.descriptions.update(cluster.descriptions)
        target.units |= cluster.units
        target.mentions += cluster.mentions
    return merged


def _entity(cluster: Cluster) -> ResolvedEntity:
    best = [d for d, _ in cluster.descriptions.most_common(2)]
    return ResolvedEntity(
        id=cluster.id, name=cluster.name, type=cluster.type,
        aliases=sorted(s for s in cluster.surface if s != cluster.name),
        description=" ".join(best)[:600], mention_count=cluster.mentions,
        source_unit_ids=sorted(cluster.units),
    )  # fmt: skip


def _end_cluster(name, allowed, types_in_unit, own_title, clusters, union, merged):
    """The merged entity at one end of a relation, or None (for example noise that was dropped)."""
    for type_ in types_in_unit.get(name.casefold(), []):
        if type_ not in allowed:
            continue
        spelled = _own_title_or(name, own_title) if type_ == "Paper" and own_title else name
        key = (type_, squash_name(spelled))
        if key in clusters:
            return merged[union.find(key)]
    return None


def _relations(results, clusters, union, merged, ontology, paper_titles) -> list[ResolvedRelation]:
    """Move every relation onto merged entities; the same edge from several units is one edge."""
    edges: dict[tuple[str, str, str], dict] = {}
    for unit_id, result in results.items():
        types_in_unit: dict[str, list[str]] = defaultdict(list)
        for entity in result.entities:
            types_in_unit[entity.name.casefold()].append(entity.type)

        own_title = paper_titles.get(unit_id, "")
        for relation in result.relations:
            predicate = next((p for p in ontology.predicates if p.name == relation.predicate), None)
            if predicate is None:
                continue
            source = _end_cluster(
                relation.source,
                predicate.from_types,
                types_in_unit,
                own_title,
                clusters,
                union,
                merged,
            )
            target = _end_cluster(
                relation.target,
                predicate.to_types,
                types_in_unit,
                own_title,
                clusters,
                union,
                merged,
            )
            if source is None or target is None or source.id == target.id:
                continue
            edge = edges.setdefault(
                (source.id, relation.predicate, target.id),
                {"descriptions": Counter(), "strengths": [], "units": []},
            )
            edge["descriptions"][relation.description] += 1
            edge["strengths"].append(relation.strength)
            if unit_id not in edge["units"]:
                edge["units"].append(unit_id)
    out = []
    for (source_id, predicate, target_id), edge in sorted(edges.items()):
        out.append(
            ResolvedRelation(
                source_id,
                predicate,
                target_id,
                edge["descriptions"].most_common(1)[0][0],
                weight=round(sum(edge["strengths"]) / 10, 2),
                confidence=round(max(edge["strengths"]) / 10, 2),
                evidence_unit_ids=sorted(edge["units"])[:MAX_EVIDENCE_PER_EDGE],
            )  # fmt: skip
        )
    return out


def save_decisions(engine: Engine, run_id: str, decisions: list[Decision]) -> None:
    """Replace the stored decisions of this run (so running again does not pile up rows)."""
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM resolution_decisions WHERE run_id = :r"), {"r": run_id})
        if decisions:
            conn.execute(
                text(
                    "INSERT INTO resolution_decisions (run_id, entity_a, entity_b, score, method,"
                    " decision, rationale) VALUES (:r, :a, :b, :s, :m, :d, :why)"
                ),
                [
                    {
                        "r": run_id,
                        "a": d.a,
                        "b": d.b,
                        "s": d.score,
                        "m": d.method,
                        "d": d.decision,
                        "why": d.rationale,
                    }
                    for d in decisions
                ],
            )
