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


INDEX_ROWS = [
    {"id": "i1", "name": "FiD", "type": "Method", "aliases": [], "mentions": 3, "sources": []},
    {"id": "i2", "name": "Natural Questions", "type": "Dataset", "aliases": ["NQ"],
     "mentions": 3, "sources": []},
    {"id": "i3", "name": "ZetaNet", "type": "Method", "aliases": [], "mentions": 1,
     "sources": []},
]  # fmt: skip
INDEX = EntityIndex(INDEX_ROWS)


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


# --- plain-words refusals, generic names, and versions the papers do not know (Phase 7) ---------


@pytest.mark.parametrize(
    "text",
    [
        "The provided context does not explicitly mention the accuracy of GPT-4 on MMLU. While "
        "there are references to GPT-3 [T1], none gives that number.",
        "The context does not provide a direct recall value for ChatGPT on TriviaQA.",
        "The provided context does not contain any information about Llama 3.",
    ],
)
def test_a_refusal_in_plain_words_is_a_refusal_with_its_own_sentence_as_the_reason(text):
    link = LinkResult("Q?", [linked(1)], 0.9)
    answer = generate(MockLlm(text), make_context(), link)
    assert answer.status == "refused" and answer.text == ""
    assert answer.reason.startswith(("The provided context", "The context")) and answer.suggestion


@pytest.mark.parametrize(
    "text",
    [
        "FiD uses DPR [T1].",
        "The context does not state the size, but T5-small has about 60M parameters [T1].",
        "KGT5 uses T5-small. The context does not mention a larger variant.",
        "The model uses the provided context to retrieve passages [T1].",
    ],
)
def test_a_real_answer_is_never_turned_into_a_refusal(text):
    link = LinkResult("Q?", [linked(1)], 0.9)
    answer = generate(MockLlm(text), make_context(), link)
    assert answer.status == "answered" and answer.text == text


def test_a_generic_word_that_is_also_an_entity_name_does_not_flag_a_sentence():
    index = EntityIndex(
        INDEX_ROWS
        + [
            {
                "id": "g",
                "name": "complex",
                "type": "Method",
                "aliases": [],
                "mentions": 5,
                "sources": [f"u_{n:012d}_0001" for n in range(12)],
            }
        ]  # fmt: skip
    )
    check = check_citations("FiD handles complex questions [T1].", make_context(), index)
    assert check.status == "verified" and check.unsupported == []
    strong = check_citations("FiD and ZetaNet [T1].", make_context(), index)
    assert strong.status == "warning" and len(strong.unsupported) == 1


def versioned_link(text_in_context=""):
    seed = Linked("e9", "claude", "Method", 1.0, "name", "Claude", False, 0.15, True, "2")
    return LinkResult("Claude 2 report?", [seed], 0.95, qualified=[seed]), text_in_context


def test_a_version_the_papers_never_mention_is_refused_before_the_model_is_called():
    link, _ = versioned_link()
    llm = MockLlm()
    answer, context = answer_local(make_deps(link), llm, link.question)
    assert answer.status == "refused" and llm.calls == 0 and context is None
    assert '"Claude"' in answer.reason and '"Claude 2"' in answer.reason


def test_a_version_the_context_does_mention_goes_on_to_the_model():
    link, _ = versioned_link()
    deps = make_deps(link)
    rows = {u: {"text": "Claude 2 was tested. " * 10, "title": "t", "paper_id": "p", "section": "s"}
            for u in ["u_000000000000_0001", "u_000000000001_0001", "u_000000000002_0001",
                      "u_000000000003_0001"]}  # fmt: skip
    deps.unit_rows = lambda ids: rows
    llm = MockLlm("Claude 2 was tested [T1].")
    answer, _ = answer_local(deps, llm, link.question)
    assert answer.status == "answered" and llm.calls == 1


def test_a_junk_entity_made_of_function_words_does_not_flag_a_sentence():
    junk = {"id": "j", "name": "part of", "type": "Method", "aliases": [], "mentions": 2,
            "sources": ["u_aaaaaaaaaaaa_0001"]}  # fmt: skip
    index = EntityIndex([*INDEX_ROWS, junk])
    check = check_citations("FiD is part of the pipeline [T1].", make_context(), index)
    assert check.status == "verified" and check.unsupported == []
