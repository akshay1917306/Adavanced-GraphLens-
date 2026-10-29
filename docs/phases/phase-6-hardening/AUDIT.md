# Phase 6 dependency and secret audit

Run on 2026-10-28. Tools: `npm audit` (npm registry advisories), `pip-audit` 
(PyPI and OSV advisories) on the exported lock files, and `gitleaks` 8.21.2 on the files and the
whole git history. An audit shows **known** advisories on the day it runs; it does not prove the
code is free of vulnerabilities.

## Results

| Scope | Tool | Result |
|---|---|---|
| Web, all packages and production only | `npm audit` | **0 vulnerabilities** |
| API, production packages (35) | `pip-audit` | **No known vulnerabilities** |
| Pipeline, production packages (138) | `pip-audit` | **2 packages with advisories** (below) |
| Files and git history (87 commits) | `gitleaks` | **No leaks.** One finding, a made-up token in a sanitiser test, is allowlisted by its exact value |
| Negative check of the scanner | `gitleaks` | A real-looking `sk-proj-...` key in a scratch folder **is** caught (exit code 1) |
| `.env` ever committed | `git log -- .env` | Never. Only `.env.example` (placeholders) is tracked |

## Pipeline findings and the decision

| Package | Version | Advisories | Fixed in | Why it is still pinned |
|---|---|---|---|---|
| `pypdf` | 6.19.0 | 11 (the one I read describes a crafted PDF that makes a call loop forever; I did not read all 11) | 6.21.2 | See below |
| `pillow` | 12.3.0 | 38 (the one I read is an out-of-bounds read in raw image decoders) | 13.0.0 | `fastembed 0.9.0` requires `pillow<13`. Moving to Pillow 13 means changing the embedding runtime (D19). The pipeline never opens or decodes an image: PDFs are read for text only and questions are text |

**pypdf.** Version 6.21.2 installs and all 400 pipeline tests pass with it. But on the 25 real
corpus PDFs it returns **different text for every one**. In the 3 I compared the difference is
whitespace only (identical after removing all whitespace), yet that changes unit text, chunk
boundaries and unit hashes, so the extraction cache misses and extraction would have to be paid
for again (Phase 2 cost about $2.40), and evidence quotes would need re-checking. For a fixed,
hash-pinned set of 25 open-licence papers, with no upload feature, that is a poor trade today.
Existing limits stay in force (file size, page count, encrypted and scanned files refused) and the
parser runs only in the command-line pipeline, never inside the API process.

**Rule (D59, confirmed by the owner on 2026-10-28):** keep `pypdf` 6.19.0 and `pillow` 12.3.0 for now as a **known, accepted
risk**; before any feature that accepts PDFs or images from other people (v1.5), upgrade `pypdf`,
re-ingest and re-baseline, and move `fastembed` and `pillow` together.

## In CI

- Job `secrets`: gitleaks over files and history (config `.gitleaks.toml`).
- Job `audit`: `npm audit --omit=dev --audit-level=high` for the web and `pip-audit` for the API.
  The pipeline is left out on purpose because of the accepted findings above; a new advisory in
  the web or API packages turns this job red, which is the intent.
