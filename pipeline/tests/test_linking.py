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


# --- weak names and version numbers (Phase 7: refusal on questions the papers cannot answer) ----


def seeds_of(question, index):
    return [group[0] for group in name_matches(question, index)]


def test_a_plain_word_name_alone_is_not_enough_but_it_is_with_a_close_question():
    index = EntityIndex([entity("a", "accuracy", "Dataset", sources=["u_a_0001", "u_a_0002"])])
    seeds = seeds_of("What accuracy does Gemini Ultra reach on SuperGLUE?", index)
    assert seeds and seeds[0].weight <= 0.5 and not seeds[0].qualified
    assert not LinkResult("q", seeds, 0.745).confident  # far from everything in the graph
    assert LinkResult("q", seeds, 0.83).confident  # close to something: go on


def test_a_real_name_is_enough_without_a_close_vector():
    index = EntityIndex([entity("k", "KGT5", sources=["u_k_0001"])])
    seeds = seeds_of("What does KGT5 use?", index)
    assert seeds[0].weight >= 0.6 and LinkResult("q", seeds, 0.0).confident


def test_a_version_number_after_a_known_name_marks_the_match_and_demotes_it():
    index = EntityIndex([entity("c", "claude", sources=["u_c_0001"])])
    plain = seeds_of("What did the authors of Claude conclude?", index)[0]
    versioned = seeds_of("What did the authors of the Claude 2 technical report conclude?", index)[
        0
    ]
    assert not plain.qualified and versioned.qualified
    assert versioned.weight == pytest.approx(plain.weight * 0.3, abs=0.01)
    seeds = [versioned]
    assert not LinkResult("q", seeds, 0.865).confident  # only a version of a known name: be strict
    assert LinkResult("q", seeds, 0.92).confident  # unless the question is very close to the graph


@pytest.mark.parametrize(
    "question", ["What about Claude v3?", "What about Claude 3.5?", "What about claude 4"]
)
def test_the_usual_ways_to_write_a_version_are_recognised(question):
    index = EntityIndex([entity("c", "claude", sources=["u_c_0001"])])
    assert seeds_of(question, index)[0].qualified


def test_a_version_that_is_part_of_a_known_name_is_not_a_mismatch():
    index = EntityIndex(
        [entity("s2", "SQuAD 2", "Dataset", sources=["u_s_0001"]), entity("s", "SQuAD", "Dataset")]
    )
    seeds = seeds_of("How is SQuAD 2 built?", index)
    assert [s.name for s in seeds] == ["SQuAD 2"] and not seeds[0].qualified


def test_a_number_that_is_not_right_after_the_name_does_not_qualify_it():
    index = EntityIndex([entity("c", "claude", sources=["u_c_0001"])])
    assert not seeds_of("Why does Claude need 2 passes?", index)[0].qualified


def test_a_versioned_name_is_kept_in_the_result_even_when_it_is_not_a_seed():
    names = [entity(f"s{i}", f"SpecificTool{i}", sources=[f"u_{i:012d}_0001"]) for i in range(6)]
    index = EntityIndex([*names, entity("c", "claude", sources=["u_c_0001"])])
    tools = " ".join(f"SpecificTool{i}" for i in range(5))
    question = f"Do {tools} and Claude 2 agree?"
    groups = name_matches(question, index)
    seeds = [g[0] for g in groups]
    assert any(s.qualified and s.qualifier == "2" for s in seeds)
    result = LinkResult("q", [], 0.0)
    result.qualified = [s for s in seeds if s.qualified]
    assert [s.matched for s in result.qualified] == ["Claude"]
