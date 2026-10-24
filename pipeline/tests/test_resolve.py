"""Entity resolution tests. The judging model is a MOCK (no network, no cost)."""

import json

import pytest

from graphlens_pipeline.extract import Entity, Relation, UnitResult
from graphlens_pipeline.llm import LlmError, LlmResult
from graphlens_pipeline.ontology import Ontology
from graphlens_pipeline.resolve import (
    acronym_fits,
    blocked_by_rules,
    build_clusters,
    is_noise,
    parenthetical_acronym,
    resolve,
    save_decisions,
    spelling_score,
    squash_name,
)
from tests.test_embed import prepare

ONTOLOGY = Ontology.model_validate(
    {
        "name": "t", "version": 1,
        "entity_types": [
            {"name": n, "description": n} for n in ("Paper", "Method", "Dataset", "Task")
        ],
        "predicates": [
            {"name": "PROPOSES", "from": ["Paper"], "to": ["Method"], "description": "x"},
            {"name": "EVALUATED_ON", "from": ["Method"], "to": ["Dataset"], "description": "x"},
            {"name": "ADDRESSES", "from": ["Method"], "to": ["Task"], "description": "x"},
        ],
    }
)  # fmt: skip


def vectors(names):
    """MOCK name embeddings: unrelated names get unrelated directions (no accidental matches)."""
    out = []
    for i, _ in enumerate(names):
        row = [0.0] * len(names)
        row[i] = 1.0
        out.append(row)
    return out


def unit(uid, entities, relations=()):
    return UnitResult(
        uid,
        [Entity(n, t, f"{n} description") for n, t in entities],
        [Relation(s, p, t, "d", st) for s, p, t, st in relations],
    )


class Judge:
    """MOCK judge: answers from a dict keyed by the two names, remembers its calls."""

    model = "gpt-4.1-mini"

    def __init__(self, answers=None, error=None):
        self.answers, self.error, self.calls = answers or {}, error, 0

    def complete(self, system, user, max_output_tokens, json_schema=None):
        self.calls += 1
        if self.error:
            raise self.error
        same = any(a in user and b in user for (a, b), v in self.answers.items() if v)
        return LlmResult(json.dumps({"same": same, "reason": "mock"}), "gpt-4.1-mini", 250, 30)


def run(results, titles=None, llm=None, **kwargs):
    return resolve(None, results, titles or {}, ONTOLOGY, vectors, llm, **kwargs)


# --- names ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("multi-hop", "Multi hop"), ("multihop", "multi-hop"), ("pre-trained", "pretrained"),
        ("Graph Neural Networks", "graph neural network"), ("Wizard of Oz", "wizard-of-oz"),
        ("Transformers (GPT)", "transformer"),
    ],
)  # fmt: skip
def test_names_that_differ_only_by_form_get_the_same_key(a, b):
    assert squash_name(a) == squash_name(b)


@pytest.mark.parametrize(
    ("a", "b"), [("T5-base", "T5-large"), ("GPT-3", "GPT-4"), ("class", "clas")]
)
def test_different_things_keep_different_keys(a, b):
    assert squash_name(a) != squash_name(b)


@pytest.mark.parametrize("name", ["q", "7", " - ", "task", "the task", "The Model"])
def test_table_header_noise_is_recognised(name):
    assert is_noise(name)


@pytest.mark.parametrize("name", ["NQ", "T5", "GAT", "reading comprehension task"])
def test_short_real_names_are_not_noise(name):
    assert not is_noise(name)


@pytest.mark.parametrize(
    ("a", "b", "reason"),
    [
        ("SQuAD", "SQuAD 2", "numbers"), ("MetaQA 1-hop", "MetaQA 3-hop", "numbers"),
        ("T5 base", "T5 large", "size"), ("with context", "without context", "negation"),
    ],
)  # fmt: skip
def test_names_that_must_never_merge_are_blocked(a, b, reason):
    assert blocked_by_rules(a, b)


def test_ordinary_variants_are_not_blocked():
    assert blocked_by_rules("KG-FiD", "KG-FiD model") is None


def test_only_a_generic_extra_word_is_safe_to_merge_unasked():
    assert spelling_score("KG-FiD", "KG-FiD model")[1] is True
    assert spelling_score("Natural Questions", "Natural Questions dataset")[1] is True
    # one character apart is NOT safe: these are two different optimizers
    adam, safe = spelling_score("Adam optimizer", "AdamW optimizer")
    assert adam >= 0.8 and safe is False
    score, safe = spelling_score("NQ reading comprehension task", "reading comprehension task")
    assert score >= 0.8 and safe is False  # looks alike, but must go to the model
    assert spelling_score("encoder-decoder model", "encoder-decoder QA model")[1] is False


@pytest.mark.parametrize(
    ("acronym", "long_name", "fits"),
    [
        ("GAT", "Graph Attention Networks (GAT)", True), ("WQSP", "WebQuestionsSP (WQSP)", True),
        ("TransE", "KGE models (TransE)", False), ("QA", "question-answering (QA) systems", True),
        ("X", "Something (X)", False),
    ],
)  # fmt: skip
def test_acronym_must_fit_the_long_form(acronym, long_name, fits):
    assert acronym_fits(acronym, long_name) is fits


def test_parenthetical_acronym_reads_only_short_letter_like_brackets():
    assert parenthetical_acronym("Graph Neural Networks (GNNs)") == "GNNs"
    assert parenthetical_acronym("method (see Section 3)") is None


# --- grouping and merging ----------------------------------------------------------------------


def test_spelling_variants_become_one_entity_with_aliases_and_all_evidence():
    results = {
        "u1": unit("u1", [("Graph Neural Networks (GNNs)", "Method"), ("HotpotQA", "Dataset")]),
        "u2": unit("u2", [("graph neural network", "Method"), ("GNN", "Method")]),
        "u3": unit("u3", [("GNNs", "Method")]),
    }
    outcome = run(results)
    methods = [e for e in outcome.entities if e.type == "Method"]
    assert len(methods) == 1  # four spellings, one thing (the bracketed acronym links "GNN")
    entity = methods[0]
    assert entity.mention_count == 4 and entity.source_unit_ids == ["u1", "u2", "u3"]
    assert {"graph neural network", "GNN"} <= set(entity.aliases) | {entity.name}


def test_same_name_in_two_types_stays_two_entities():
    results = {"u1": unit("u1", [("Alpha", "Method"), ("Alpha", "Dataset")])}
    assert sorted(e.type for e in run(results).entities) == ["Dataset", "Method"]


def test_noise_is_dropped_and_counted():
    results = {"u1": unit("u1", [("q", "Dataset"), ("HotpotQA", "Dataset")])}
    outcome = run(results)
    assert [e.name for e in outcome.entities] == ["HotpotQA"] and outcome.dropped_noise == 1


def test_a_shortened_paper_title_is_mapped_to_the_real_title():
    title = "Uncertainty Guided Global Memory Improves Multi-Hop Question Answering"
    results = {
        "u1": unit(
            "u1",
            [("Uncertainty Guided Global Memory", "Paper"), ("GEMFormer", "Method")],
            [("Uncertainty Guided Global Memory", "PROPOSES", "GEMFormer", 9)],
        ),
        "u2": unit(
            "u2", [(title, "Paper"), ("GEMFormer", "Method")], [(title, "PROPOSES", "GEMFormer", 8)]
        ),
    }
    outcome = run(results, {"u1": title, "u2": title})
    papers = [e for e in outcome.entities if e.type == "Paper"]
    assert [p.name for p in papers] == [title]
    assert len(outcome.relations) == 1 and outcome.relations[0].evidence_unit_ids == ["u1", "u2"]


def test_a_cited_paper_with_another_title_is_not_turned_into_the_current_paper():
    results = {"u1": unit("u1", [("Attention Is All You Need", "Paper")])}
    outcome = run(results, {"u1": "Uncertainty Guided Global Memory Improves Multi-Hop QA"})
    assert [e.name for e in outcome.entities] == ["Attention Is All You Need"]


# --- relations ------------------------------------------------------------------------------------


def test_relations_move_onto_merged_entities_and_repeated_edges_become_one():
    results = {
        "u1": unit(
            "u1", [("Paper One", "Paper"), ("KG-FiD", "Method")],
            [("Paper One", "PROPOSES", "KG-FiD", 6)],
        ),
        "u2": unit(
            "u2", [("Paper One", "Paper"), ("KG-FiD model", "Method")],
            [("Paper One", "PROPOSES", "KG-FiD model", 10)],
        ),
    }  # fmt: skip
    outcome = run(results)
    assert len(outcome.entities) == 2  # "KG-FiD" and "KG-FiD model" are merged (a generic tail)
    (edge,) = outcome.relations
    assert edge.predicate == "PROPOSES" and edge.evidence_unit_ids == ["u1", "u2"]
    assert edge.weight == 1.6 and edge.confidence == 1.0  # strengths 6 and 10


def test_every_kept_edge_has_evidence_and_both_ends_exist():
    results = {
        "u1": unit("u1", [("Alpha", "Method"), ("Beta", "Dataset"), ("q", "Task")],
                   [("Alpha", "EVALUATED_ON", "Beta", 7), ("Alpha", "ADDRESSES", "q", 7)]),
    }  # fmt: skip
    outcome = run(results)
    ids = {e.id for e in outcome.entities}
    assert len(outcome.relations) == 1  # the edge to the dropped noise entity is gone
    for edge in outcome.relations:
        assert edge.evidence_unit_ids and edge.source_id in ids and edge.target_id in ids


def test_ids_are_stable_between_runs():
    results = {"u1": unit("u1", [("KG-FiD", "Method")]), "u2": unit("u2", [("Kg Fid", "Method")])}
    assert [e.id for e in run(results).entities] == [e.id for e in run(results).entities]


# --- the model-judged gray zone -------------------------------------------------------------------


GRAY = {
    "u1": unit("u1", [("NQ reading comprehension task", "Task")]),
    "u2": unit("u2", [("reading comprehension task", "Task")]),
}


def test_the_gray_zone_is_not_merged_without_a_model():
    outcome = run(GRAY)
    assert len(outcome.entities) == 2 and outcome.unasked_pairs == 1
    assert [d.method for d in outcome.decisions] == ["rejected"]


def test_the_model_can_merge_and_can_refuse():
    names = ("NQ reading comprehension task", "reading comprehension task")
    yes = run(GRAY, llm=Judge({names: True}))
    assert len(yes.entities) == 1 and yes.decisions[0].method == "llm" and yes.model_calls == 1
    no = run(GRAY, llm=Judge())
    assert len(no.entities) == 2 and no.decisions[0].decision == "keep_separate"


def test_the_cost_cap_leaves_remaining_pairs_unmerged():
    judge = Judge({("a", "b"): True})
    outcome = run(GRAY, llm=judge, max_cost_usd=0.0)
    assert judge.calls == 0 and outcome.unasked_pairs == 1 and len(outcome.entities) == 2


def test_a_failing_model_never_merges():
    outcome = run(GRAY, llm=Judge(error=LlmError("model call failed (TimeoutError)")))
    assert len(outcome.entities) == 2 and outcome.unasked_pairs == 1


def test_numbers_block_a_merge_even_if_the_model_would_agree():
    results = {"u1": unit("u1", [("SQuAD", "Dataset")]), "u2": unit("u2", [("SQuAD 2", "Dataset")])}
    judge = Judge({("SQuAD", "SQuAD 2"): True})
    outcome = run(results, llm=judge)
    assert len(outcome.entities) == 2 and judge.calls == 0


def test_clusters_report_mentions_and_noise():
    clusters, mentions, noise = build_clusters(
        {"u": unit("u", [("x", "Method"), ("HotpotQA", "Dataset")])}, {}
    )
    assert (mentions, noise, len(clusters)) == (2, 1, 1)


# --- decisions are stored once ---------------------------------------------------------------


@pytest.mark.integration
def test_decisions_are_saved_and_replaced_not_piled_up(engine, tmp_path):
    from sqlalchemy import text

    from graphlens_pipeline.runs import start_run

    prepare(engine, tmp_path)
    run_ = start_run(engine, "embed corpus", "idx-resolve-test", {}, 1.0, sample=True)
    decisions = run(GRAY, llm=Judge()).decisions
    save_decisions(engine, run_.id, decisions)
    save_decisions(engine, run_.id, decisions)
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM resolution_decisions WHERE run_id = :r"), {"r": run_.id}
        ).scalar_one()
        row = conn.execute(
            text("SELECT method, decision FROM resolution_decisions WHERE run_id = :r"),
            {"r": run_.id},
        ).one()
    assert count == 1 and tuple(row) == ("llm", "keep_separate")
