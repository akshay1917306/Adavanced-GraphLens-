"""Step 1 of local search: clean the question and link it to entities of the graph.

Nothing here calls a paid model. Linking uses two free signals:
- a name match: word groups of the question (longest first) are compared with every entity name
  and alias, ignoring case, hyphens, spaces and a plural "s";
- the vector index of entity embeddings (the local bge model).
A name that belongs to more than one entity (for example "QA" as a method and as a task) is
reported as ambiguous instead of being guessed. Every candidate gets a weight: specific names
that appear in few papers weigh most, plain words and names found everywhere weigh little.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field

from graphlens_pipeline.resolve import EMPTY_WORDS, is_noise, squash_name

MAX_QUESTION_CHARS = 4000
REDACTED = "[redacted]"
MAX_SEEDS = 5
MAX_PER_AMBIGUOUS_GROUP = 2
VECTOR_TOP_K = 10
MAX_NGRAM = 5
INDEX_NAME = "entity_embedding"
# Neo4j's cosine score is (1 + cosine) / 2. On this corpus every in-corpus question scored at
# least 0.81 and every out-of-corpus one at most 0.77, so 0.79 separates them (calibrated on 40
# in-corpus and 8 out-of-corpus questions, 2026-10-26; the margin is small).
MIN_VECTOR_SCORE = 0.79
PAPERS_IN_CORPUS = 25
# A name match weighs at most 0.5 when it is a plain word ("accuracy", "claude") and up to 1.0
# when it looks like a real name. A plain-word match alone is not enough to answer: the question
# must also be close to something in the graph. Measured on the 60 answerable development
# questions, the closest graph entity always scored at least 0.81, while a question about things
# the papers do not contain scored 0.75 ("accuracy of Gemini Ultra on SuperGLUE").
STRONG_NAME_WEIGHT = 0.6
# "Claude 2": the corpus knows "claude", the question asks about a version it does not know. Such a
# match is demoted, and the question then needs a much closer graph match before it is answered.
QUALIFIED_MIN_VECTOR = 0.90
QUALIFIED_FACTOR = 0.3
VERSION_WORD = re.compile(r"^v?\d+(?:\.\d+)*$", re.IGNORECASE)

SECRET_PATTERNS = {
    "key": [
        re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),  # OpenAI style, also sk-proj-...
        re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),  # GitHub tokens
        re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
        re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),  # Slack tokens
    ],
    "token": [
        re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}"),
        re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"),  # JWT
        re.compile(
            r"\b(?=[A-Za-z0-9_\-]{32,}\b)(?=[A-Za-z0-9_\-]*\d)(?=[A-Za-z0-9_\-]*[A-Za-z])"
            r"[A-Za-z0-9_\-]{32,}\b"
        ),  # a long mixed token
    ],
    "password": [
        re.compile(
            r"(?i)\b(?:password|passwd|secret|api[_\- ]?key|access[_\- ]?token)\s*[:=]\s*\S+"
        )
    ],
    "email": [re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")],
}

# Question words and generic words that must never link on their own.
STOP_WORDS = EMPTY_WORDS | {
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how", "does", "did", "do",
    "is", "are", "was", "were", "be", "been", "can", "could", "would", "should", "will", "the",
    "and", "for", "with", "from", "that", "this", "these", "those", "than", "then", "there",
    "paper", "papers", "corpus", "work", "works", "study", "studies", "approach", "approaches",
    "technique", "techniques", "result", "results", "question", "questions", "answer", "answers",
    "between", "about", "used", "use", "using", "uses", "compare", "compared", "related",
    "improve", "improves", "improved", "evaluate", "evaluated", "propose", "proposed",
    "introduce", "introduced", "mention", "mentioned", "describe", "described", "show", "shows",
}  # fmt: skip


class EmptyQuestion(ValueError):
    pass


@dataclass
class Sanitised:
    text: str
    redactions: dict[str, int] = field(default_factory=dict)
    truncated: bool = False


@dataclass(frozen=True)
class Linked:
    id: str
    name: str
    type: str
    score: float  # 1.0 for a name match, the vector score otherwise
    source: str  # "name" or "vector"
    matched: str = ""  # the words of the question that matched
    ambiguous: bool = False  # the same words also name another entity
    weight: float = 1.0  # how much to trust it as a starting point (0 to 1)
    qualified: bool = False  # a version number follows the name in the question ("Claude 2")


@dataclass
class LinkResult:
    question: str
    seeds: list[Linked] = field(default_factory=list)
    best_vector_score: float = 0.0
    ambiguous_groups: list[list[Linked]] = field(default_factory=list)

    @property
    def has_name_match(self) -> bool:
        return any(s.source == "name" for s in self.seeds)

    @property
    def confident(self) -> bool:
        """Enough to go on.

        A real name (strong weight) is enough. A plain-word name needs the question to be close to
        something in the graph as well. If the only names found are followed by a version number the
        corpus does not know ("Claude 2"), the question must be very close to the graph."""
        names = [s for s in self.seeds if s.source == "name"]
        if any(not s.qualified and s.weight >= STRONG_NAME_WEIGHT for s in names):
            return True
        if names and all(s.qualified for s in names):
            return self.best_vector_score >= QUALIFIED_MIN_VECTOR
        return self.best_vector_score >= MIN_VECTOR_SCORE


def sanitise(question: str) -> Sanitised:
    """At most 4,000 characters, no control characters, secrets and emails redacted."""
    text = unicodedata.normalize("NFKC", question)
    text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    text = " ".join(text.split())
    if not text:
        raise EmptyQuestion("the question is empty")
    redactions: dict[str, int] = {}
    for kind, patterns in SECRET_PATTERNS.items():
        for pattern in patterns:
            text, count = pattern.subn(REDACTED, text)
            if count:
                redactions[kind] = redactions.get(kind, 0) + count
    truncated = len(text) > MAX_QUESTION_CHARS
    return Sanitised(text[:MAX_QUESTION_CHARS], redactions, truncated)


class EntityIndex:
    """Every entity name and alias of one index version, in memory (about 1,500 entities)."""

    def __init__(self, entities: list[dict]) -> None:
        self.by_key: dict[str, list[dict]] = {}
        generic = {squash_name(w) for w in STOP_WORDS}
        for entity in entities:
            for name in [entity["name"], *(entity.get("aliases") or [])]:
                key = squash_name(name)
                if len(key) < 2 or key in generic or is_noise(name):
                    continue
                bucket = self.by_key.setdefault(key, [])
                if all(e["id"] != entity["id"] for e in bucket):
                    bucket.append(entity)
        self.by_id = {e["id"]: e for e in entities}

    @staticmethod
    def papers(entity: dict) -> int:
        """In how many papers the entity appears (the paper part of its unit IDs); at least 1."""
        sources = entity.get("sources") or []
        return max(1, len({u.split("_")[1] for u in sources if u.count("_") >= 2}))

    @classmethod
    def from_neo4j(cls, driver, index_version: str, database: str = "neo4j") -> EntityIndex:
        with driver.session(database=database) as session:
            rows = [
                dict(r)
                for r in session.run(
                    "MATCH (e:Entity {index_version: $v}) RETURN e.id AS id, e.name AS name,"
                    " e.type AS type, e.aliases AS aliases, e.mention_count AS mentions,"
                    " e.source_unit_ids AS sources ORDER BY e.id",
                    v=index_version,
                )
            ]  # fmt: skip
        return cls(rows)


_WORD = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9\-+.']*[A-Za-z0-9])?")


def _words(question: str) -> list[str]:
    return [w.rstrip(".'") for w in _WORD.findall(question)]


def _looks_like_a_name(word: str) -> bool:
    """A capital inside ("FiD", "DPR") or a digit marks a real name, not a plain word."""
    return any(c.isupper() for c in word[1:]) or any(c.isdigit() for c in word)


def _usable_single(word: str) -> bool:
    """A one-word name needs to look like a name, or be a plain word of 4 or more letters."""
    if word.casefold() in STOP_WORDS:
        return False
    return len(word) >= 4 or _looks_like_a_name(word)


def _name_weight(gram: str, papers: int) -> float:
    """Specific names (several words, or a capital or digit inside) weigh more than plain words;
    a name found in many papers ("question answering") weighs less than a rare one."""
    plain_word = " " not in gram and not _looks_like_a_name(gram)
    rarity = math.log(PAPERS_IN_CORPUS / min(papers, PAPERS_IN_CORPUS)) / math.log(PAPERS_IN_CORPUS)
    return round((0.5 if plain_word else 1.0) * max(0.15, min(1.0, rarity)), 3)


def name_matches(question: str, index: EntityIndex) -> list[list[Linked]]:
    """Groups of entities named in the question. A group has several members when the same words
    name several entities (ambiguous). Longer word groups win; words already used are skipped."""
    words = _words(question)
    used = [False] * len(words)
    groups: list[tuple[int, list[Linked]]] = []
    for size in range(min(MAX_NGRAM, len(words)), 0, -1):
        for start in range(len(words) - size + 1):
            if any(used[start : start + size]):
                continue
            gram = " ".join(words[start : start + size])
            if size == 1 and not _usable_single(gram):
                continue
            entities = index.by_key.get(squash_name(gram))
            if not entities:
                continue
            for i in range(start, start + size):
                used[i] = True
            many = len(entities) > 1
            ordered = sorted(entities, key=lambda e: (-(e.get("mentions") or 0), e["id"]))
            # a longer match was tried first, so a version number right after the name belongs to a
            # thing the corpus does not know ("Claude 2" when only "claude" exists)
            following = words[start + size] if start + size < len(words) else ""
            qualified = bool(VERSION_WORD.match(following))
            factor = QUALIFIED_FACTOR if qualified else 1.0
            members = [
                Linked(
                    e["id"], e["name"], e["type"], 1.0, "name", gram, many,
                    round(_name_weight(gram, index.papers(e)) * factor, 3), qualified,
                )
                for e in ordered
            ]  # fmt: skip
            groups.append((start, members))
    groups.sort(key=lambda g: g[0])  # in the order they appear in the question
    return [members for _, members in groups]


def vector_matches(
    driver,
    embed_query,
    question: str,
    index_version: str,
    top_k: int = VECTOR_TOP_K,
    database: str = "neo4j",
) -> list[Linked]:
    vector = [float(x) for x in embed_query(question)]
    with driver.session(database=database) as session:
        rows = list(
            session.run(
                "CALL db.index.vector.queryNodes($index, $k, $q) YIELD node, score"
                " WHERE node.index_version = $v"
                " RETURN node.id AS id, node.name AS name, node.type AS type, score"
                " ORDER BY score DESC",
                index=INDEX_NAME, k=top_k * 4, q=vector, v=index_version,
            )
        )  # fmt: skip
    return [
        Linked(
            r["id"], r["name"], r["type"], float(r["score"]), "vector", "", False,
            round(max(0.2, min(1.0, (float(r["score"]) - MIN_VECTOR_SCORE) / 0.15)), 3),
        )
        for r in rows[:top_k]
    ]  # fmt: skip


def link_question(
    driver,
    embed_query,
    index: EntityIndex,
    question: str,
    index_version: str,
    min_vector_score: float = MIN_VECTOR_SCORE,
    max_seeds: int = MAX_SEEDS,
) -> LinkResult:
    """Clean the question and pick up to `max_seeds` starting entities.

    Candidates are the name matches (at most 2 per ambiguous name) and the vector hits above
    `min_vector_score`. They are ranked by weight, name matches first on a tie."""
    clean = sanitise(question)
    result = LinkResult(clean.text)
    groups = name_matches(clean.text, index)
    result.ambiguous_groups = [g for g in groups if len(g) > 1]
    candidates = [entity for group in groups for entity in group[:MAX_PER_AMBIGUOUS_GROUP]]
    hits = vector_matches(driver, embed_query, clean.text, index_version)
    result.best_vector_score = max((h.score for h in hits), default=0.0)
    candidates += [h for h in hits if h.score >= min_vector_score]
    seen: set[str] = set()
    for candidate in sorted(candidates, key=lambda c: (-c.weight, c.source != "name", c.id)):
        if candidate.id not in seen and len(result.seeds) < max_seeds:
            result.seeds.append(candidate)
            seen.add(candidate.id)
    return result
