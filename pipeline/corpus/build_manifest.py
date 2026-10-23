"""Pick question-answering papers from the ACL Anthology and write a license manifest.

Only papers from ACL-family main conferences published in 2016 or later are eligible,
because the Anthology copyright policy licenses those under CC BY 4.0
(https://aclanthology.org/faq/copyright/). The manifest records the evidence for every paper.

Standard library only. Run from the repository root:

    python pipeline/corpus/build_manifest.py --count 25
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

XML_URL = "https://raw.githubusercontent.com/acl-org/acl-anthology/master/data/xml/{name}.xml"
# ACL-family main conferences (the license policy covers ACL materials from 2016 on).
SOURCES = ["2022.acl", "2023.acl", "2022.emnlp", "2023.emnlp"]
# Only full-paper volumes, not demos, tutorials or workshops.
ALLOWED_VOLUMES = {"long", "main"}
KEYWORDS = ("question answering", "multi-hop", "reading comprehension", "qa")
# Keep the corpus on text question answering: skip dialogue, images and tables.
EXCLUDE = (
    "dialogue",
    "chatbot",
    "conversational",
    "image",
    "visual",
    "video",
    "table",
    "tabular",
    "speech",
)
LICENSE = "CC BY 4.0"
LICENSE_BASIS = "https://aclanthology.org/faq/copyright/"
USER_AGENT = "GraphLens-corpus-builder/0.1 (research project; contact: repo owner)"
FIELDS = [
    "paper_id",
    "title",
    "year",
    "venue",
    "authors",
    "pdf_url",
    "page_url",
    "license",
    "license_basis_url",
    "retrieved_on",
    "sha256",
    "bytes",
]


@dataclass(frozen=True)
class Paper:
    paper_id: str
    title: str
    year: str
    venue: str
    authors: str


def fetch(url: str, attempts: int = 3) -> bytes:
    """Download a URL with a bounded number of retries."""
    if not url.startswith("https://"):
        raise ValueError("only https URLs are allowed")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
                return response.read()
        except (TimeoutError, OSError) as error:
            if attempt == attempts:
                raise
            print(f"retry {attempt}/{attempts - 1} for {url}: {type(error).__name__}")
            time.sleep(2 * attempt)
    raise RuntimeError("unreachable")


def parse_source(name: str, data: bytes) -> list[Paper]:
    # The Anthology files declare no entities. Refuse any that do, which also blocks
    # entity-expansion attacks, instead of adding a dependency for this small script.
    if b"<!ENTITY" in data or b"<!DOCTYPE" in data:
        raise ValueError(f"{name}: unexpected DTD in XML, refusing to parse")
    root = ET.fromstring(data)  # noqa: S314
    year = name.split(".")[0]
    venue = name.split(".")[1].upper()
    papers: list[Paper] = []
    for volume in root.iter("volume"):
        if volume.get("id") not in ALLOWED_VOLUMES:
            continue
        for paper in volume.iter("paper"):
            title_el = paper.find("title")
            if title_el is None:
                continue
            title = " ".join("".join(title_el.itertext()).split())
            lowered = title.lower()
            words = set(lowered.replace(":", " ").replace("-", " ").split())
            if not (any(k in lowered for k in KEYWORDS[:3]) or "qa" in words):
                continue
            if any(word in lowered for word in EXCLUDE):
                continue
            authors = [
                " ".join(filter(None, (a.findtext("first"), a.findtext("last"))))
                for a in paper.findall("author")
            ]
            paper_id = f"{name}-{volume.get('id')}.{paper.get('id')}"
            papers.append(Paper(paper_id, title, year, venue, "; ".join(authors[:3])))
    return papers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=25)
    parser.add_argument("--out", type=Path, default=Path("data/corpus/qa_v0/manifest.csv"))
    args = parser.parse_args()

    per_source: list[list[Paper]] = []
    for name in SOURCES:
        per_source.append(
            sorted(parse_source(name, fetch(XML_URL.format(name=name))), key=lambda p: p.paper_id)
        )
    # Round-robin across sources so one venue does not dominate; deterministic order.
    chosen: list[Paper] = []
    index = 0
    while len(chosen) < args.count and any(index < len(group) for group in per_source):
        for group in per_source:
            if index < len(group) and len(chosen) < args.count:
                chosen.append(group[index])
        index += 1

    today = dt.date.today().isoformat()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for paper in chosen:
            anthology_id = paper.paper_id
            writer.writerow(
                {
                    "paper_id": anthology_id,
                    "title": paper.title,
                    "year": paper.year,
                    "venue": paper.venue,
                    "authors": paper.authors,
                    "pdf_url": f"https://aclanthology.org/{anthology_id}.pdf",
                    "page_url": f"https://aclanthology.org/{anthology_id}/",
                    "license": LICENSE,
                    "license_basis_url": LICENSE_BASIS,
                    "retrieved_on": today,
                    "sha256": "",
                    "bytes": "",
                }
            )
    print(f"Wrote {len(chosen)} papers to {args.out}")


if __name__ == "__main__":
    main()
