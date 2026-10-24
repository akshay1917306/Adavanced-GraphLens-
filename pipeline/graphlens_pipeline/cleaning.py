"""Turn raw PDF page text into clean sections.

Steps: normalise characters, drop page numbers and running headers, join words split by an
end-of-line hyphen, find section headings, and stop at the References heading.

Known limit: joining "multi-" and "hop" at a line end gives "multihop" (we cannot tell a
real hyphenated word from a layout hyphen). Fine for retrieval; do not use for quotes.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

# Boilerplate printed on the first page of ACL Anthology papers.
BOILERPLATE = (
    re.compile(r"^Proceedings of the\b", re.I),
    re.compile(r"^V ?olume \d+:.*\bpages\b", re.I),
    re.compile(r"(c©|©)\s?\d{4}"),
    re.compile(r"^Association for Computational Linguistics$", re.I),
)
PAGE_NUMBER = re.compile(r"\d{1,5}")
CONTACT_LINE = re.compile(r"@|https?://|www\.", re.I)  # emails and web addresses
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")  # keeps tab and newline
NAMED_HEADING = re.compile(
    r"(abstract|introduction|related work|background|conclusions?|limitations|"
    r"ethics statement|acknowledg(e)?ments|references|bibliography|appendix)",
    re.I,
)
# "3 Method" or "3.1 Input Format": no period after the number (that is a list item like
# "3. Does it work?"), plain characters only (algorithm lines contain symbols).
NUMBERED_HEADING = re.compile(r"\d{1,2}(\.\d{1,2}){0,2}\s+[A-Z][A-Za-z0-9 ,:;'&/()\-]{1,80}")
SMALL_WORDS = {"of", "and", "the", "for", "in", "on", "to", "with", "a", "an", "via", "by",
               "from", "vs", "at", "as", "or", "using", "over", "under", "into"}  # fmt: skip
STOP_HEADING = re.compile(r"(references|bibliography)", re.I)
DROPPED_SECTION = re.compile(
    r"acknowledg(e)?ments", re.I
)  # thanks and funders: no research content
MIN_BODY_BEFORE_REFERENCES = 500  # a "References" line this early is not the bibliography


@dataclass(frozen=True)
class Section:
    name: str
    text: str


def _sanitise(page: str) -> str:
    """Normalise characters and remove ones Postgres cannot store (NUL, other control codes)."""
    page = unicodedata.normalize("NFKC", page)
    page = page.encode("utf-8", errors="ignore").decode("utf-8")  # drops lone surrogates
    return CONTROL_CHARS.sub("", page)


def _is_boilerplate(line: str) -> bool:
    return any(pattern.search(line) for pattern in BOILERPLATE)


def _looks_like_title(title: str) -> bool:
    """Most important words start with a capital letter ("Results and Discussion")."""
    content = [word for word in title.split() if word.lower() not in SMALL_WORDS]
    if not content:
        return False
    capitalised = sum(1 for word in content if word[0].isupper() or word[0].isdigit())
    return capitalised / len(content) >= 0.5


def _is_heading(line: str) -> bool:
    if len(line.split()) > 12 or line.endswith("-"):
        return False
    if NAMED_HEADING.fullmatch(line):
        return True
    if not NUMBERED_HEADING.fullmatch(line):
        return False
    title = line.split(None, 1)[1]
    return not title.split()[-1].isdigit() and _looks_like_title(title)


def _is_heading_continuation(line: str) -> bool:
    """A long heading can wrap onto a second, short line (for example a last word alone)."""
    return (
        len(line.split()) <= 3
        and line[:1].isupper()
        and not line.endswith((".", ",", ":", ";", "-"))
    )


def _repeated_lines(pages: list[list[str]]) -> set[str]:
    """Lines that repeat on many pages (running headers and footers), digits ignored."""
    if len(pages) < 3:
        return set()
    counts: Counter[str] = Counter()
    for lines in pages:
        counts.update({re.sub(r"\d+", "#", line) for line in lines if len(line) < 120})
    threshold = max(3, round(0.4 * len(pages)))
    return {line for line, count in counts.items() if count >= threshold}


def clean_pages(pages: list[str]) -> list[Section]:
    """Return the body of a paper as sections. An empty list means no usable text."""
    normalised = [[line.strip() for line in _sanitise(page).splitlines()] for page in pages]
    repeated = _repeated_lines([[ln for ln in lines if ln] for lines in normalised])

    lines: list[str] = []
    for page_lines in normalised:
        for line in page_lines:
            if not line or PAGE_NUMBER.fullmatch(line) or _is_boilerplate(line):
                continue
            if re.sub(r"\d+", "#", line) in repeated:
                continue
            lines.append(line)

    sections: list[tuple[str, list[str]]] = [("Front matter", [])]
    body_chars = 0
    may_wrap = False  # the previous line was a numbered heading
    for line in lines:
        if _is_heading(line):
            if STOP_HEADING.fullmatch(line) and body_chars >= MIN_BODY_BEFORE_REFERENCES:
                break
            sections.append((line, []))
            may_wrap = NUMBERED_HEADING.fullmatch(line) is not None
            continue
        if may_wrap and _is_heading_continuation(line):
            name, body = sections[-1]
            sections[-1] = (f"{name} {line}", body)
            may_wrap = False
            continue
        may_wrap = False
        sections[-1][1].append(line)
        body_chars += len(line)

    # The front matter (title, authors, affiliations) is kept: it is the evidence for AUTHORED_BY
    # and AFFILIATED_WITH (CR-0003). Lines with an email or web address are removed from it.
    sections[0] = (sections[0][0], [ln for ln in sections[0][1] if not CONTACT_LINE.search(ln)])

    result: list[Section] = []
    for name, body_lines in sections:
        text = _join_lines(body_lines)
        if text and not DROPPED_SECTION.fullmatch(name):
            result.append(Section(name=name, text=text))
    return result


def _join_lines(lines: list[str]) -> str:
    """Join lines into running text, merging words split by an end-of-line hyphen."""
    parts: list[str] = []
    for line in lines:
        if parts and parts[-1].endswith("-") and line[:1].islower():
            parts[-1] = parts[-1][:-1] + line
        else:
            parts.append(line)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()
