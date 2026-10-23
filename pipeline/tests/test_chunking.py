import pytest

from graphlens_pipeline.chunking import (
    OVERLAP_TOKENS,
    TARGET_TOKENS,
    chunk_sections,
    get_encoding,
    split_sentences,
)
from graphlens_pipeline.cleaning import Section
from tests.conftest import sentences

ENC = get_encoding()


def test_chunks_never_exceed_target_and_are_numbered_in_order():
    chunks = chunk_sections([Section("Intro", sentences(200))], ENC)
    assert len(chunks) > 3
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert all(c.token_count <= TARGET_TOKENS for c in chunks)
    assert all(c.token_count == len(ENC.encode(c.text)) for c in chunks)


def test_full_chunks_are_close_to_target():
    chunks = chunk_sections([Section("Intro", sentences(200))], ENC)
    assert all(c.token_count > TARGET_TOKENS - 60 for c in chunks[:-2])


def test_consecutive_chunks_overlap():
    chunks = chunk_sections([Section("Intro", sentences(200))], ENC)
    for left, right in zip(chunks, chunks[1:], strict=False):
        shared = set(split_sentences(left.text)) & set(split_sentences(right.text))
        assert shared, "chunks should share at least one sentence"
        overlap_tokens = sum(len(ENC.encode(s)) for s in shared)
        assert overlap_tokens <= OVERLAP_TOKENS


def test_no_sentence_is_lost():
    text = sentences(120)
    chunks = chunk_sections([Section("Intro", text)], ENC)
    covered = {s for c in chunks for s in split_sentences(c.text)}
    assert covered == set(split_sentences(text))


def test_chunks_do_not_cross_section_boundaries():
    sections = [Section("A", sentences(100, "alpha")), Section("B", sentences(100, "beta"))]
    chunks = chunk_sections(sections, ENC)
    assert {c.section for c in chunks} == {"A", "B"}
    for chunk in chunks:
        other = "beta" if chunk.section == "A" else "alpha"
        assert other not in chunk.text
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))


def test_one_very_long_sentence_is_cut_by_tokens():
    long_sentence = "Word " * 2000 + "end."
    chunks = chunk_sections([Section("Body", long_sentence)], ENC)
    assert len(chunks) >= 3
    assert all(c.token_count <= TARGET_TOKENS for c in chunks)


def test_short_section_gives_one_chunk():
    chunks = chunk_sections([Section("Abstract", "A short abstract. It has two sentences.")], ENC)
    assert len(chunks) == 1 and chunks[0].section == "Abstract"


def test_empty_input_gives_no_chunks():
    assert chunk_sections([], ENC) == []
    assert chunk_sections([Section("Empty", "   ")], ENC) == []


def test_is_deterministic():
    sections = [Section("A", sentences(150))]
    assert chunk_sections(sections, ENC) == chunk_sections(sections, ENC)


def test_overlap_must_be_smaller_than_target():
    with pytest.raises(ValueError):
        chunk_sections([Section("A", "x. y.")], ENC, target=100, overlap=100)


def test_abbreviation_does_not_split_a_sentence():
    parts = split_sentences("The method of Smith et al. 2020 works. It is fast.")
    assert parts == ["The method of Smith et al. 2020 works.", "It is fast."]
