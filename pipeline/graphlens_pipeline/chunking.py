"""Split sections into text units of at most 450 tokens with 75 tokens of overlap.

The blueprint says about 600 tokens, but the embedding model (bge-base) reads only 512, so
longer units would lose their tail. CR-0002 lowers the target; see docs/adr/CR-0002.

Blueprint 2.5: text units respect section boundaries, so a chunk never mixes two sections.
Chunks end at sentence boundaries. A single sentence longer than the limit is cut by tokens.
Tokens are counted with tiktoken (o200k_base, the vocabulary of the gpt-4.1 and gpt-5 models).
"""

import re
from dataclasses import dataclass

import tiktoken

from graphlens_pipeline.cleaning import Section

ENCODING_NAME = "o200k_base"
TARGET_TOKENS = 450
OVERLAP_TOKENS = 75
CHUNKER_VERSION = "2"

SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
ABBREVIATIONS = (
    "et al.", "e.g.", "i.e.", "Fig.", "Figs.", "Eq.", "Sec.", "Tab.", "No.", "vs.", "cf.",
)  # fmt: skip


@dataclass(frozen=True)
class Chunk:
    ordinal: int
    section: str
    text: str
    token_count: int


def get_encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(ENCODING_NAME)


def split_sentences(text: str) -> list[str]:
    """Split on sentence ends, but not after common abbreviations such as "et al."."""
    pieces = SENTENCE_BREAK.split(text)
    sentences: list[str] = []
    for piece in pieces:
        if sentences and sentences[-1].endswith(ABBREVIATIONS):
            sentences[-1] = f"{sentences[-1]} {piece}"
        else:
            sentences.append(piece)
    return [s for s in sentences if s.strip()]


def _split_long_sentence(sentence: str, enc: tiktoken.Encoding, target: int) -> list[str]:
    tokens = enc.encode(sentence)
    return [enc.decode(tokens[i : i + target]) for i in range(0, len(tokens), target)]


def _fit(sentences: list[str], enc: tiktoken.Encoding, target: int) -> tuple[str, list[str]]:
    """Join sentences into one text of at most `target` tokens; return it and any leftovers."""
    kept = list(sentences)
    leftovers: list[str] = []
    while len(kept) > 1 and len(enc.encode(" ".join(kept))) > target:
        leftovers.insert(0, kept.pop())
    return " ".join(kept), leftovers


def chunk_sections(
    sections: list[Section],
    enc: tiktoken.Encoding | None = None,
    target: int = TARGET_TOKENS,
    overlap: int = OVERLAP_TOKENS,
) -> list[Chunk]:
    """Chunk every section. Ordinals count up across the whole document."""
    if overlap >= target:
        raise ValueError("overlap must be smaller than the target size")
    enc = enc or get_encoding()
    chunks: list[Chunk] = []

    for section in sections:
        sentences: list[str] = []
        for sentence in split_sentences(section.text):
            if len(enc.encode(sentence)) > target:
                sentences.extend(_split_long_sentence(sentence, enc, target))
            else:
                sentences.append(sentence)

        window: list[str] = []  # sentences of the chunk being built (overlap first)
        window_tokens = 0
        new_count = 0  # trailing sentences of `window` not yet written to any chunk
        for sentence in sentences:
            tokens = len(enc.encode(sentence))
            if window and window_tokens + tokens > target:
                text, leftovers = _fit(window, enc, target)
                chunks.append(_make_chunk(len(chunks), section.name, text, enc))
                written = window[: len(window) - len(leftovers)]
                window = _overlap_tail(written, enc, overlap) + leftovers
                window_tokens = sum(len(enc.encode(s)) for s in window)
                new_count = len(leftovers)
                if window_tokens + tokens > target:  # the overlap does not fit; drop it
                    window = leftovers
                    window_tokens = sum(len(enc.encode(s)) for s in window)
            window.append(sentence)
            window_tokens += tokens
            new_count += 1
        while new_count > 0 and window:  # write what is left (loops again only on a rare overflow)
            text, leftovers = _fit(window, enc, target)
            chunks.append(_make_chunk(len(chunks), section.name, text, enc))
            window = leftovers
            new_count = len(leftovers)
    return chunks


def _overlap_tail(sentences: list[str], enc: tiktoken.Encoding, overlap: int) -> list[str]:
    """The last sentences of a chunk that together stay within `overlap` tokens."""
    tail: list[str] = []
    total = 0
    for sentence in reversed(sentences):
        tokens = len(enc.encode(sentence))
        if total + tokens > overlap:
            break
        tail.insert(0, sentence)
        total += tokens
    return tail


def _make_chunk(ordinal: int, section: str, text: str, enc: tiktoken.Encoding) -> Chunk:
    return Chunk(ordinal=ordinal, section=section, text=text, token_count=len(enc.encode(text)))
