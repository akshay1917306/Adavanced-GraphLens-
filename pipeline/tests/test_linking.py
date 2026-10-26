"""Tests for the question sanitiser and entity linking. No model is called; the vector part runs
against the real Neo4j with throwaway entities and hand-made vectors."""

from __future__ import annotations

import uuid

import pytest

from graphlens_pipeline.linking import (
    MAX_QUESTION_CHARS,
    REDACTED,
    EmptyQuestion,
    EntityIndex,
    Linked,
    LinkResult,
    link_question,
    name_matches,
    sanitise,
    vector_matches,
)

# --- the sanitiser ------------------------------------------------------------------------


def test_keys_tokens_passwords_and_emails_are_redacted_and_counted():
    question = (
        "My key is sk-proj-abcdEFGH1234567890xyz and mail me at a.b@example.com, "
        "also Bearer abcdefghijklmnop1234 and password=hunter2 please: what is DPR?"
    )
    clean = sanitise(question)
    for secret in ("sk-proj", "a.b@example.com", "abcdefghijklmnop1234", "hunter2"):
        assert secret not in clean.text
    assert clean.text.count(REDACTED) >= 4 and "what is DPR?" in clean.text
    assert set(clean.redactions) == {"key", "email", "token", "password"}


def test_a_long_mixed_token_is_redacted_but_a_unit_id_is_not():
    token = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7"
    assert token not in sanitise(f"what about {token}?").text
    assert "u_85db020b91cb_0001" in sanitise("see u_85db020b91cb_0001").text


def test_long_questions_are_cut_and_control_characters_removed():
    clean = sanitise("a" * 5000)
    assert len(clean.text) == MAX_QUESTION_CHARS and clean.truncated
    assert sanitise("hello\x00 \x07world\n\nok").text == "hello world ok"


@pytest.mark.parametrize("empty", ["", "   ", "\x00\x01"])
def test_an_empty_question_is_refused(empty):
    with pytest.raises(EmptyQuestion):
        sanitise(empty)


# --- name matching ------------------------------------------------------------------------


def entity(eid, name, type_="Method", aliases=(), mentions=1, sources=()):
    return {
        "id": eid, "name": name, "type": type_, "aliases": list(aliases), "mentions": mentions,
        "sources": list(sources),
    }  # fmt: skip


INDEX = EntityIndex(
    [
        entity("e1", "Fusion-in-Decoder", aliases=["FiD"], mentions=9),
        entity("e2", "Natural Questions", "Dataset", aliases=["NQ"], mentions=7),
        entity("e3", "QA", "Method", mentions=2),
        entity("e4", "QA", "Task", mentions=5),
        entity("e5", "dense passage retrieval", aliases=["DPR"], mentions=6),
        entity("e6", "model", mentions=3),  # generic, must never link
        entity("e7", "KG-FiD", mentions=4),
    ]
)


def linked_names(question):
    return [[m.name for m in group] for group in name_matches(question, INDEX)]


def test_names_aliases_hyphens_and_plurals_all_match():
    assert linked_names("How does FiD use Natural Questions?") == [
        ["Fusion-in-Decoder"], ["Natural Questions"]
    ]  # fmt: skip
    assert linked_names("Which fusion in decoder variants exist?") == [["Fusion-in-Decoder"]]
    assert linked_names("Is dense passage retrievals useful?") == [["dense passage retrieval"]]
    assert linked_names("Does NQ help DPR?") == [["Natural Questions"], ["dense passage retrieval"]]


def test_the_longest_words_win_and_are_not_matched_twice():
    assert linked_names("Why is KG-FiD better than FiD?") == [["KG-FiD"], ["Fusion-in-Decoder"]]


def test_generic_words_and_question_words_never_link():
    assert linked_names("Which model does the paper use to answer questions?") == []
    assert linked_names("what is the best approach") == []


def test_a_name_shared_by_two_entities_is_ambiguous_and_the_busier_one_comes_first():
    groups = name_matches("How is QA evaluated?", INDEX)
    assert len(groups) == 1 and [m.type for m in groups[0]] == ["Task", "Method"]
    assert all(m.ambiguous for m in groups[0])


def test_an_ambiguous_name_gives_at_most_two_seeds_and_a_close_question_is_confident():
    many = EntityIndex([entity(f"q{i}", "QA", mentions=10 - i) for i in range(4)])
    assert len(name_matches("How is QA evaluated?", many)[0]) == 4  # all are reported
    result = LinkResult("q", [], 0.80)
    assert result.confident and not LinkResult("q", [], 0.70).confident
    named = LinkResult("q", [Linked("x", "n", "Method", 1.0, "name")], 0.0)
    assert named.confident


def test_rare_specific_names_weigh_more_than_plain_words_and_names_found_everywhere():
    wide = [f"u_{n:012d}_0001" for n in range(20)]  # a name found in 20 of the 25 papers
    index = EntityIndex(
        [
            entity("r1", "DILR", sources=["u_aaaaaaaaaaaa_0001"]),
            entity("r2", "retrieval", sources=["u_aaaaaaaaaaaa_0002"]),
            entity("r3", "Question Answering Everywhere", sources=wide),
        ]
    )
    weights = {
        g[0].name: g[0].weight
        for g in name_matches("DILR and retrieval and Question Answering Everywhere", index)
    }
    assert weights["DILR"] == 1.0 and weights["retrieval"] == 0.5
    assert weights["Question Answering Everywhere"] < 0.35


def test_short_names_need_to_look_like_names():
    assert linked_names("is nq good") == []  # lower case two letters: not a name
    assert linked_names("Is NQ good?") == [["Natural Questions"]]


# --- the vector part, against the real Neo4j ------------------------------------------------


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


def vec(x):
    return [1.0, x] + [0.0] * 766


@pytest.mark.integration
def test_vector_hits_are_filtered_by_version_and_added_after_name_matches(driver_and_version):
    driver, version = driver_and_version
    with driver.session() as session:
        for eid, name, x in [("v1", "Alpha method", 0.9), ("v2", "Beta method", 0.4),
                             ("v3", "Gamma dataset", 0.1)]:  # fmt: skip
            session.run(
                "CREATE (e:Entity {id: $id, name: $name, type: 'Method', index_version: $v,"
                " aliases: []}) WITH e CALL db.create.setNodeVectorProperty(e, 'embedding', $vec)",
                id=f"{version}-{eid}", name=name, v=version, vec=vec(x),
            ).consume()  # fmt: skip
    hits = vector_matches(driver, lambda q: vec(1.0), "anything", version, top_k=2)
    assert [h.name for h in hits] == ["Alpha method", "Beta method"]
    assert all(h.source == "vector" for h in hits)
    index = EntityIndex(
        [entity(f"{version}-v2", "Beta method"), entity("other", "Delta method", mentions=1)]
    )
    result = link_question(
        driver, lambda q: vec(1.0), index, "What about Beta method and sk-abcdefghijklmnopqrst?",
        version, min_vector_score=0.0, max_seeds=3,
    )  # fmt: skip
    assert [s.source for s in result.seeds] == ["name", "vector", "vector"]
    assert result.seeds[0].name == "Beta method" and REDACTED in result.question
    assert "sk-abcdefghijklmnopqrst" not in result.question
    high = link_question(
        driver, lambda q: vec(1.0), EntityIndex([]), "no names here at all", version,
        min_vector_score=0.9999,
    )  # fmt: skip
    assert high.seeds == [] and high.best_vector_score > 0
