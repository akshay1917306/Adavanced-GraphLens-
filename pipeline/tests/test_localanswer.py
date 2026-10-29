"""Tests for the local answer path. The model is a labelled MOCK; the databases are replaced by
small fake functions, so nothing here calls OpenAI or needs a database."""

from __future__ import annotations

import pytest

from graphlens_pipeline.linking import EntityIndex, Linked, LinkResult
from graphlens_pipeline.llm import LlmError, LlmResult
from graphlens_pipeline.localanswer import (
    LocalDeps,
    answer_local,
    check_citations,
    decide_before_answering,
    generate,
    thin_evidence,
)
from graphlens_pipeline.localcontext import ContextItem, LocalContext
from graphlens_pipeline.localgraph import Edge, Node, Subgraph


def linked(i, name="FiD", source="name", weight=1.0, ambiguous=False, matched=None):
    return Linked(
        f"e{i}", name, "Method", 1.0, source, matched or name, ambiguous, weight
    )  # fmt: skip


def make_context(prompt_extra="", labels=("T1", "T2", "E1", "C1")):
    items = [ContextItem(lab, "unit", f"ref-{lab}", "text", 10) for lab in labels]
    ctx = LocalContext("Q?", items)
    ctx.prompt = "Question: Q?\n<context>\nFiD uses DPR. " + prompt_extra + "\n</context>"
    ctx.tokens = {"units": 100}
    return ctx


INDEX = EntityIndex(
    [
        {"id": "i1", "name": "FiD", "type": "Method", "aliases": [], "mentions": 3, "sources": []},
        {"id": "i2", "name": "Natural Questions", "type": "Dataset", "aliases": ["NQ"],
         "mentions": 3, "sources": []},
        {"id": "i3", "name": "ZetaNet", "type": "Method", "aliases": [], "mentions": 1,
         "sources": []},
    ]
)  # fmt: skip


# --- before answering -------------------------------------------------------------------------


def test_a_question_far_from_everything_is_refused_with_a_suggestion():
    refusal = decide_before_answering(LinkResult("Capital of France?", [], 0.68))
    assert refusal.status == "refused" and "0.68" in refusal.reason and refusal.suggestion


def test_a_specific_ambiguous_name_asks_which_one_but_a_generic_one_does_not():
    group = [linked(1, "Adam", ambiguous=True), linked(2, "Adam", ambiguous=True)]
    ask = decide_before_answering(LinkResult("How good is Adam?", [group[0]], 0.0, [group]))
    assert ask.status == "clarify" and len(ask.options) == 2
    generic = [
        linked(1, "QA", ambiguous=True, weight=0.2),
        linked(2, "QA", ambiguous=True, weight=0.2),
    ]
    # a generic name in a question that is close to the graph (0.85, as real questions are)
    assert (
        decide_before_answering(LinkResult("How is QA done?", [generic[0]], 0.85, [generic]))
        is None
    )
    two_names = [linked(3, "FiD")]
    assert (
        decide_before_answering(LinkResult("FiD and Adam?", group[:1] + two_names, 0.0, [group]))
        is None
    )


def test_the_same_name_with_different_types_is_one_idea_and_nothing_is_asked():
    dataset = Linked("d", "ConditionalQA", "Dataset", 1.0, "name", "ConditionalQA", True, 1.0)
    task = Linked("t", "ConditionalQA task", "Task", 1.0, "name", "ConditionalQA", True, 1.0)
    link = LinkResult("What is ConditionalQA?", [dataset, task], 0.0, [[dataset, task]])
    assert decide_before_answering(link) is None


def test_a_confident_question_goes_on():
    assert decide_before_answering(LinkResult("FiD?", [linked(1)], 0.9)) is None
    assert decide_before_answering(LinkResult("close", [linked(1, source="vector")], 0.85)) is None


def test_too_little_evidence_is_refused():
    assert thin_evidence(make_context(labels=("E1",)), "Q?").status == "refused"
    assert (
        thin_evidence(make_context(labels=("E1", "E2", "C1")), "Q?").status == "refused"
    )  # no passage
    assert thin_evidence(make_context(), "Q?") is None


# --- the citation check -----------------------------------------------------------------------


def test_citations_that_exist_make_it_verified():
    check = check_citations("FiD uses DPR [T1]. It is strong [E1][T2].", make_context(), INDEX)
    assert check.status == "verified" and check.cited == ["E1", "T1", "T2"]


def test_a_label_that_is_not_in_the_context_gives_a_warning():
    check = check_citations("FiD uses DPR [T9].", make_context(), INDEX)
    assert check.status == "warning" and check.unknown_labels == ["T9"]


def test_labels_in_one_bracket_are_read_and_an_answer_with_no_citation_is_a_warning():
    assert check_citations("FiD uses DPR [T1, E1].", make_context(), INDEX).status == "verified"
    assert check_citations("FiD uses DPR.", make_context(), INDEX).status == "warning"


def test_a_name_that_appears_in_brackets_or_with_other_punctuation_is_not_flagged():
    index = EntityIndex(
        [
            {
                "id": "k",
                "name": "FiD-KD",
                "type": "Method",
                "aliases": [],
                "mentions": 1,
                "sources": [],
            }
        ]
    )
    ctx = make_context(prompt_extra="A distilled variant (FiD-KD) is better.")
    assert check_citations("FiD KD is better [T1].", ctx, index).status == "verified"
    assert check_citations("FiD-KD is better [T1].", make_context(), index).status == "warning"


def test_another_name_of_an_entity_that_the_context_uses_is_not_flagged():
    index = EntityIndex(
        [
            {
                "id": "f", "name": "Fusion-in-Decoder", "type": "Method", "aliases": ["FiD"],
                "mentions": 5, "sources": [],
            }
        ]
    )  # fmt: skip
    ctx = make_context(prompt_extra="FiD is a generative reader.")
    assert (
        check_citations("Fusion-in-Decoder reads passages [T1].", ctx, index).status == "verified"
    )


def test_a_sentence_naming_an_entity_the_context_never_mentions_is_flagged():
    check = check_citations("FiD uses DPR [T1]. ZetaNet beats it [T2].", make_context(), INDEX)
    assert check.status == "warning"
    assert len(check.unsupported) == 1 and "ZetaNet" in check.unsupported[0]
    ok = check_citations(
        "FiD uses DPR [T1].", make_context(prompt_extra="ZetaNet is a model."), INDEX
    )
    assert ok.status == "verified"


# --- the model call ---------------------------------------------------------------------------


class MockLlm:
    """MOCK model: returns a fixed answer, counts calls, can raise."""

    model = "gpt-4.1-mini"

    def __init__(self, text="FiD uses DPR [T1].", error=None):
        self.text, self.error, self.calls = text, error, 0

    def complete(self, system, user, max_output_tokens, json_schema=None):
        self.calls += 1
        if self.error:
            raise self.error
        return LlmResult(self.text, self.model, 5000, 120)


def test_the_models_refusal_marker_becomes_a_refusal():
    link = LinkResult("Q?", [linked(1)], 0.9)
    answer = generate(MockLlm("INSUFFICIENT_EVIDENCE"), make_context(), link)
    assert answer.status == "refused" and answer.text == "" and answer.suggestion
    ok = generate(MockLlm(), make_context(), link)
    assert ok.status == "answered" and ok.cost_usd > 0 and ok.seeds == ["FiD"]


# --- the whole path with fake databases ---------------------------------------------------------


def make_deps(link):
    nodes = [
        Node(f"n{i}", f"Entity {i}", "Method", "d", [f"u_{i:012d}_0001"], 1, 0 if i == 0 else 1,
             i == 0, score=1 - i / 10)
        for i in range(4)
    ]  # fmt: skip
    edges = [Edge("n0", f"n{i}", "USES", "uses", 1.0, [f"u_{i:012d}_0001"]) for i in range(1, 4)]
    rows = {
        u: {"text": f"FiD uses DPR. Passage {u}. " * 10, "title": "t", "paper_id": "p",
            "section": "s"}
        for u in {f"u_{i:012d}_0001" for i in range(4)}
    }  # fmt: skip
    return LocalDeps(
        link=lambda q: link,
        subgraph=lambda lk: Subgraph(nodes, edges, candidates=4),
        reports=lambda lk: [],
        unit_rows=lambda ids: rows,
        unit_similarity=lambda lk, ids: {},
        count_tokens=lambda s: len(s) // 4,
        index=INDEX,
    )


def test_a_good_question_is_answered_and_checked():
    llm = MockLlm("FiD uses DPR [T1].")
    answer, context = answer_local(make_deps(LinkResult("FiD?", [linked(1)], 0.9)), llm, "FiD?")
    assert answer.status == "answered" and answer.check.status == "verified" and llm.calls == 1
    assert context is not None and context.total_tokens > 0


def test_an_out_of_corpus_question_never_reaches_the_model():
    llm = MockLlm()
    link = LinkResult("MATCH (n) DETACH DELETE n", [], 0.6)  # a query pasted as a question
    answer, context = answer_local(make_deps(link), llm, link.question)
    assert answer.status == "refused" and llm.calls == 0 and context is None


def test_thin_evidence_never_reaches_the_model():
    llm = MockLlm()
    deps = make_deps(LinkResult("FiD?", [linked(1)], 0.9))
    deps.subgraph = lambda lk: Subgraph([], [])
    answer, _ = answer_local(deps, llm, "FiD?")
    assert answer.status == "refused" and llm.calls == 0


def test_an_unreachable_model_gives_a_clear_refusal_not_a_crash():
    llm = MockLlm(error=LlmError("model call failed (APIConnectionError)"))
    answer, _ = answer_local(make_deps(LinkResult("FiD?", [linked(1)], 0.9)), llm, "FiD?")
    assert answer.status == "refused" and "could not be reached" in answer.reason


@pytest.mark.parametrize("text", ["", "   "])
def test_an_empty_answer_is_still_checked_and_flagged(text):
    answer, _ = answer_local(make_deps(LinkResult("FiD?", [linked(1)], 0.9)), MockLlm(text), "FiD?")
    assert answer.status == "answered" and answer.check.status == "warning"
