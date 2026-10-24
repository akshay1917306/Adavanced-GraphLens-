from graphlens_pipeline.cleaning import clean_pages
from tests.conftest import fake_pages


def names(pages):
    return [section.name for section in clean_pages(pages)]


def test_finds_sections_keeps_front_matter_and_cuts_references():
    sections = clean_pages(fake_pages())
    assert [s.name for s in sections] == ["Front matter", "Abstract", "1 Introduction", "2 Method"]
    front = sections[0].text
    assert "A Paper About Things" in front and "Jane Author" in front  # CR-0003
    joined = " ".join(s.text for s in sections)
    assert "must be dropped" not in joined  # the bibliography is cut
    assert "Proceedings of the" not in joined


def test_front_matter_loses_email_and_web_lines_but_keeps_authors_and_affiliations():
    pages = [
        "A Paper About Things\nJane Author, John Writer\nUniversity of Examples\n"
        "{jane,john}@example.edu\nhttps://example.edu/jane\nwww.example.edu\n"
        "Abstract\nShort abstract with a link https://example.org/code kept in the body.\n"
        "1 Introduction\n" + "Real body text of the paper goes here. " * 12
    ]
    sections = clean_pages(pages)
    front = sections[0].text
    assert sections[0].name == "Front matter"
    assert "Jane Author" in front and "University of Examples" in front
    assert "@" not in front and "http" not in front and "www" not in front
    assert "https://example.org/code" in sections[1].text  # only the front matter is filtered


def test_a_paper_without_front_matter_gets_no_empty_front_matter_section():
    assert (
        names(["Abstract\nShort abstract.\n1 Introduction\n" + "Body text of the paper. " * 20])[0]
        == "Abstract"
    )


def test_removes_page_numbers():
    pages = [
        "Abstract\nBody text of the first page. " + "word " * 100 + "\n1605",
        "More body text on the second page.\n1606",
    ]
    text = " ".join(s.text for s in clean_pages(pages))
    assert "1605" not in text and "1606" not in text
    assert "second page" in text


def test_joins_hyphenated_line_ends():
    pages = ["Abstract\nThe retrieval system is unsu-\npervised and works well. " * 1 + "x" * 600]
    text = clean_pages(pages)[0].text
    assert "unsupervised" in text


def test_normalises_ligatures():
    pages = ["Abstract\nThe ﬁnal ﬂow of the eﬃcient method. " + "word " * 200]
    text = clean_pages(pages)[0].text
    assert "final flow" in text and "efficient" in text


def test_removes_characters_postgres_cannot_store():
    pages = [
        "Abstract\nA clean\x00 sentence with a NUL, a bell\x07 and a lone \ud800 surrogate. "
        + "word " * 200
    ]
    text = clean_pages(pages)[0].text
    assert "\x00" not in text and "\x07" not in text and "\ud800" not in text
    assert "A clean sentence with a NUL" in text


BODY = "Real body text of the paper goes here. " * 12


def test_list_items_algorithm_lines_and_table_rows_are_not_headings():
    pages = [
        "Abstract\nShort abstract of the paper.\n1 Introduction\n" + BODY + "\n"
        "1. Does the new method improve the baseline on all datasets?\n"
        "3. Does each component con-\ntribute to better performance?\n"
        "12 Q←Q∪{ qi,{q i1}} ; 13 end\n2 TrainMq which transforms action\n"
        "4 Results 5\n" + BODY
    ]
    assert names(pages) == ["Abstract", "1 Introduction"]


def test_wrapped_two_line_heading_is_one_section():
    pages = [
        "Abstract\nShort abstract.\n2 Attribution for Cross-Lingual Question\nAnswering\n" + BODY
    ]
    assert names(pages) == ["Abstract", "2 Attribution for Cross-Lingual Question Answering"]


def test_normal_headings_still_work():
    pages = [
        "Abstract\nShort abstract.\n3.1 Input Format\n"
        + BODY
        + "\n6 Results and discussion\n"
        + BODY
    ]
    assert names(pages) == ["Abstract", "3.1 Input Format", "6 Results and discussion"]


def test_acknowledgements_are_dropped():
    pages = [
        "Abstract\nShort abstract.\n1 Introduction\n"
        + BODY
        + "\nAcknowledgements\nWe thank the reviewers and our funders.\n7 Conclusion\n"
        + BODY
    ]
    result = clean_pages(pages)
    assert [s.name for s in result] == ["Abstract", "1 Introduction", "7 Conclusion"]
    assert not any("funders" in s.text for s in result)


def test_ignores_early_references_word():
    # A "References" line before any real body text must not end the paper.
    pages = ["Abstract\nShort.\nReferences\nTiny.\n1 Introduction\n" + "Real body text. " * 80]
    assert "1 Introduction" in names(pages)


def test_drops_lines_repeated_on_many_pages():
    page = "Running Header Title\nSome unique body line number {n} with words.\n{n}"
    pages = ["Abstract\n" + page.format(n=1)] + [page.format(n=n) for n in range(2, 7)]
    text = " ".join(s.text for s in clean_pages(pages))
    assert "Running Header Title" not in text


def test_empty_and_blank_input_gives_no_sections():
    assert clean_pages([]) == []
    assert clean_pages(["", "   \n  ", "12"]) == []
