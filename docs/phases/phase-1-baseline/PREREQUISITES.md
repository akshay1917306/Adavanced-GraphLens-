# Phase 1 prerequisites (owner)

| # | What | Why | Status |
|---|---|---|---|
| 1 | Phase 0 approved, merged and tagged `phase-0` | Phase 1 builds on it | Done |
| 2 | Corpus topic chosen | Needed to download papers | Done: QA from ACL Anthology |
| 3 | OpenAI API key in the local `.env` as `OPENAI_API_KEY` | Baseline answers and judging | **Owner to do** |
| 4 | Monthly spending limit set in the OpenAI dashboard | A budget alert is not a hard cap, so set a limit you can afford | **Owner to do** |
| 5 | About 5 GB free disk and Docker Desktop with 6 GB or more memory | Models, vectors, containers | Check |
| 6 | Internet access for one-time downloads (papers, about 450 MB embedding model) | Local embeddings run offline afterwards | Check |

## How to put the key in `.env`

1. Open `.env` in the repository folder (copy from `.env.example` if it is missing).
2. Replace the placeholder after `OPENAI_API_KEY=` with your key.
3. Save. Never paste the key in chat, issues or screenshots. `.env` is ignored by Git.

Claude can check that the setting exists without printing the value.

## Costs

- Embeddings and sparse vectors: local, free.
- OpenAI: baseline answers for 40 questions and (later) judging. Small. Claude shows an
  estimate and asks for approval before any batch run.
- Papers: free (CC BY).
