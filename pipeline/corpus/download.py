"""Download the PDFs listed in a corpus manifest and record their hash and size.

Rules: one request per second, bounded retries, a size limit, and a check that the file
really is a PDF. Files that already exist and match their recorded hash are skipped, so
the script can be re-run safely. Standard library only. Run from the repository root:

    python pipeline/corpus/download.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import time
import urllib.request
from pathlib import Path

USER_AGENT = "GraphLens-corpus-builder/0.1 (research project; contact: repo owner)"
MAX_BYTES = 10 * 1024 * 1024  # a research paper PDF should be well below this
DELAY_SECONDS = 1.0
ATTEMPTS = 3


def download(url: str) -> bytes:
    """Fetch one URL, retrying a few times, refusing anything larger than MAX_BYTES."""
    if not url.startswith("https://"):
        raise ValueError("only https URLs are allowed")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError(f"file larger than {MAX_BYTES} bytes")
            return data
        except (TimeoutError, OSError) as error:
            if attempt == ATTEMPTS:
                raise
            print(f"  retry {attempt}/{ATTEMPTS - 1}: {type(error).__name__}")
            time.sleep(2 * attempt)
    raise RuntimeError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/corpus/qa_v0/manifest.csv"))
    parser.add_argument("--out", type=Path, default=Path("data/corpus/qa_v0/pdfs"))
    args = parser.parse_args()

    with args.manifest.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    args.out.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    for row in rows:
        target = args.out / f"{row['paper_id']}.pdf"
        if target.exists() and row["sha256"]:
            if hashlib.sha256(target.read_bytes()).hexdigest() == row["sha256"]:
                print(f"skip   {row['paper_id']} (already downloaded)")
                continue
        print(f"get    {row['paper_id']}")
        try:
            data = download(row["pdf_url"])
        except (OSError, ValueError) as error:
            print(f"  FAILED: {type(error).__name__}: {error}")
            failures.append(row["paper_id"])
            continue
        finally:
            time.sleep(DELAY_SECONDS)
        if not data.startswith(b"%PDF"):
            print("  FAILED: not a PDF")
            failures.append(row["paper_id"])
            continue
        target.write_bytes(data)
        row["sha256"] = hashlib.sha256(data).hexdigest()
        row["bytes"] = str(len(data))

    with args.manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    done = sum(1 for row in rows if row["sha256"])
    total_mb = sum(int(row["bytes"] or 0) for row in rows) / 1_000_000
    print(f"Done: {done}/{len(rows)} papers, {total_mb:.1f} MB. Failed: {failures or 'none'}")


if __name__ == "__main__":
    main()
