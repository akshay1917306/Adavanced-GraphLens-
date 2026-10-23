# Corpus qa_v0 (development corpus)

Question-answering papers from ACL-family main conferences (ACL and EMNLP, 2022 and 2023).

## License basis

The ACL Anthology copyright policy (https://aclanthology.org/faq/copyright/) says material
published in or after 2016 is available under Creative Commons Attribution 4.0 (CC BY 4.0).
The policy page was read on the retrieval date in `manifest.csv`.

Limits of this evidence:

- It is the Anthology's policy, not a check of each PDF. The policy page also says other
  materials are copyrighted by their respective holders. Papers from ACL-family main
  conferences are covered, and nothing else is used.
- This is a development corpus, not legal advice. Recheck before publishing the data.
- Keep the author and title credit (CC BY needs attribution).

## Files

| File | What |
|---|---|
| `manifest.csv` | One row per paper: ID, title, authors, URLs, license, license evidence URL, retrieval date, SHA-256, size |
| `pdfs/` | Downloaded PDFs. Git-ignored; rebuild with `pipeline/corpus/download.py` |

## Rebuild

From the repository root (standard library only):

```bash
python pipeline/corpus/build_manifest.py --count 25   # choose papers (fetches Anthology metadata)
python pipeline/corpus/download.py                    # download PDFs, fill sha256 and bytes
```
