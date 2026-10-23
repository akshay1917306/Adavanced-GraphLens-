# Phase 1 walkthrough: Baseline RAG and evaluation set v0

## 1. What we built

The **plain vector RAG** that GraphRAG must beat later, plus a way to measure it.

- A **corpus**: 25 question-answering papers from ACL and EMNLP 2022 and 2023, with a license
  manifest (all recorded as CC BY 4.0).
- **Ingest**: read each PDF, clean the text, cut it into small passages ("text units"), and
  store them in Postgres. Running it twice adds nothing.
- **Embeddings**: turn every passage into numbers (dense, for meaning, and sparse, for exact
  words) with models that run on your own computer, and store them in Qdrant.
- **Baseline answer**: find the best 6 passages for a question, ask `gpt-4.1-mini` to answer
  only from them with `[1]`-style citations, and check that the citation numbers are real.
- **Evaluation set v0**: 30 local and 10 global questions with reference answers and exact
  evidence quotes, reviewed by the owner.
- **Evaluation runner**: runs the baseline on those 40 questions, scores them, and records
  cost. A **dry run** shows the cost first.
- A **Prefect flow** that runs ingest and embed together with retries.

Nothing here builds a graph. That starts in Phase 2.

## 2. How it works, step by step

1. **License manifest** (`pipeline/corpus/build_manifest.py`). Picks QA papers from the ACL
   Anthology metadata. Only ACL-family papers from 2016 on are used, because the Anthology's
   policy page says they are CC BY 4.0. The manifest stores where each paper came from.
2. **Download** (`download.py`). One request per second, retries, size limit, checks that the
   file is a PDF, and stores each file's SHA-256 hash (a fingerprint) in the manifest.
3. **Read** (`pdf.py`). pypdf reads the text. It refuses empty, encrypted, scanned, huge or
   corrupt files with a short error message.
4. **Clean** (`cleaning.py`). Fixes ligatures (`ﬁ` becomes `fi`), joins words split at line
   ends, drops page numbers and running headers, removes characters Postgres cannot store,
   finds section headings, drops author lines before the abstract, cuts at "References", and
   drops "Acknowledgements".
5. **Chunk** (`chunking.py`). Splits each section at sentence ends into units of at most 450
   tokens with 75 tokens of overlap. A unit never crosses a section boundary.
6. **Store** (`ingest.py`). One transaction per paper: the document row and all its units, or
   nothing. A paper with the same hash is skipped. A paper whose license is not plain CC BY is
   refused.
7. **Embed** (`embed.py`). `bge-base-en-v1.5` gives 768 numbers per unit (meaning); `BM25`
   gives a sparse vector (exact words such as "ConditionalQA"). Both go to one Qdrant
   collection. Only vectors and a small label go there; the text stays in Postgres.
8. **Ask** (`answer.py`, `llm.py`). The question is embedded, Qdrant finds 20 candidates by
   meaning and 20 by words, and they are merged (RRF, a rank-merging method) into the best 6.
   Their text is read from Postgres, numbered, and sent to the model with strict rules: use
   only these passages, cite every fact, treat passage text as data not instructions, and say
   `INSUFFICIENT_EVIDENCE` when the passages are not enough.
9. **Check** (`answer.py`). Every `[n]` must match a passage that was sent. A refusal shows no
   evidence. If nothing is retrieved, the program refuses without calling the model.
10. **Evaluate** (`evalset.py`, `evalrun.py`). Runs steps 8 and 9 for 40 questions, then a
    judge model compares each answer with the reference answer. It also measures how many
    evidence quotes were inside the passages that were sent.

**Example.** Question: "What are conditional answers in the ConditionalQA dataset?" The
passages come from the ConditionalQA paper, the answer says the answers apply only when
certain conditions hold and cites `[1]`, and `[1]` is the paper's abstract passage.

## 3. Important files

| File | Job |
|---|---|
| `pipeline/graphlens_pipeline/cleaning.py` | Turns messy PDF text into clean sections |
| `pipeline/graphlens_pipeline/chunking.py` | Cuts sections into 450-token units with overlap |
| `pipeline/graphlens_pipeline/ingest.py` | Writes documents and units to Postgres, safe to repeat |
| `pipeline/graphlens_pipeline/embed.py` | Local models and the Qdrant collection |
| `pipeline/graphlens_pipeline/answer.py` | Search, context, prompt, citation check |
| `pipeline/graphlens_pipeline/llm.py` | The only code that calls OpenAI; limits, retries, cost |
| `pipeline/graphlens_pipeline/evalset.py`, `evalrun.py` | Question checker, runner, judge, results |
| `pipeline/graphlens_pipeline/flow.py` | Prefect flow: ingest then embed |
| `pipeline/graphlens_pipeline/__main__.py` | The command line |
| `pipeline/corpus/` | Scripts that build and download the corpus manifest |
| `data/corpus/qa_v0/manifest.csv` | The 25 papers, licenses, hashes (PDFs stay out of Git) |
| `data/eval/v0/questions.json`, `REVIEW.md`, `results/` | Questions, review page, baseline results |
| `docs/DECISIONS.md` (D15 to D21), `docs/adr/CR-0002-chunk-size-450.md` | Why things are the way they are |

## 4. Tools and why

- We used **pypdf** because in our test it kept normal word spacing and read two-column pages
  in order. We did not choose **pdfminer.six** because it glued words together on all 5 test
  papers, and we did not choose **PyMuPDF** because its AGPL license is a risk for a public
  repository.
- We used **tiktoken** to count tokens the way the OpenAI models do. Chunk sizes and costs
  depend on it.
- We used **bge-base-en-v1.5 through fastembed** because it runs on your own CPU for free and
  the file is small (about 210 MB, int8-quantised). We did not choose the full PyTorch model
  because it is about twice the size and needs the heavy PyTorch library. Quantising can lower
  quality a little; this was not measured.
- We used **BM25 sparse vectors** next to the dense ones because paper-specific names are found
  by exact words, not by meaning. We did not choose dense-only search because a name like
  "HopFuse" may sit near unrelated text in meaning space.
- We used **Qdrant** (blueprint choice) for vectors and kept the text in **Postgres**, so there
  is one source of truth for text.
- We used **`gpt-4.1-mini`** because it is cheap ($0.40 and $1.60 per million tokens in and out,
  from the pricing page on 2026-10-24) and answered well in tests. We did not choose a bigger
  model because the baseline only needs to be a fair, plain RAG, and cost matters. The owner
  can change `LLM_MODEL_MAIN` in `.env`.
- We used **Prefect** (blueprint choice) for retries and logs. Its cost is 78 more packages
  and a FastAPI version pin (D21). Resume works because the stages are idempotent, not because
  of Prefect.
- We used **Docker** for everything, so nothing needs installing on Windows except Docker
  Desktop. Ubuntu/WSL is optional.

## 5. How to run it

Open **PowerShell** in the repository folder (`Adavanced-GraphLens-`). Docker Desktop must be
running. You need a `.env` with your own passwords and `OPENAI_API_KEY` (copy `.env.example`;
never share `.env`).

```bash
docker compose up -d                                    # Postgres, Neo4j, Qdrant, Redis, API
docker compose run --rm pipeline index                  # ingest + embed (about 5 minutes the first time)
docker compose run --rm pipeline ask "What makes ConditionalQA hard?"   # costs about $0.001
```

| What | URL or port |
|---|---|
| API health | http://localhost:8000/api/v1/health |
| Qdrant dashboard | http://localhost:6333/dashboard |
| Postgres | `localhost:5432` (local only) |

The first run of `index` needs the PDFs. If `data/corpus/qa_v0/pdfs/` is empty, run the two
corpus scripts first with any Python 3.11 or newer:
`python pipeline/corpus/build_manifest.py --count 25` then `python pipeline/corpus/download.py`.

The evaluation (the dry run costs nothing; the real run costs about $0.05):

```bash
docker compose run --rm pipeline eval-load
docker compose run --rm pipeline eval-run --dry-run
$env:GIT_SHA = git rev-parse --short HEAD
docker compose run --rm -v "${PWD}/data/eval/v0/results:/out" pipeline eval-run --max-cost-usd 0.25
```

**Stop:** `docker compose down` (keeps data) or `docker compose down -v` (also deletes data).

**Common problems**

| Problem | Fix |
|---|---|
| `Cannot connect to the Docker daemon` | Start Docker Desktop and wait until it says running |
| `Cannot start: OPENAI_API_KEY is not set` | Put your key in `.env`, then run the command again |
| A pull fails with a TLS or token error | Your internet dropped; run the command again |
| First `index` is slow | It loads the models once per run; later runs are faster |

## 6. How to test it

```bash
docker compose up -d postgres qdrant
docker compose run --rm --entrypoint pytest pipeline -q          # 106 tests
docker compose run --rm --no-deps --entrypoint ruff pipeline check .
docker compose run --rm pipeline eval-verify                     # every evidence quote exists
```

The integration tests create their own temporary database and Qdrant collections and remove
them, so your real data is not touched. Tests that would call OpenAI use a mock (`FakeLlm`,
`FakeEmbedder`) and say so in their names.

## 7. Actual results (2026-10-24, run by Claude on the owner's Windows machine)

- Ingest: 25 of 25 papers, **726 text units** (17 to 450 tokens, average 308). A second run
  added nothing. After CR-0002 (450 instead of 600 tokens), 3 units (0.4%) are still longer
  than the embedding model's 512-token limit.
- Embeddings: 726 points in Qdrant, 282 seconds for the first run, nothing new on the second.
- Tests: **106 pass**; `ruff` is clean. CI for the `pipeline/` folder is written but has **not
  run on GitHub yet**.
- Baseline on evaluation set v0 (`gpt-4.1-mini`, 6 passages, cost **$0.05245**, 133 seconds):

| | All | Local (30) | Global (10) |
|---|---|---|---|
| Correct (LLM judge) | 70% | 93% | 0% |
| Supporting-fact coverage | 68% | 88% | 9% |
| Citation numbers valid | 100% | 100% | 100% |

Reading it: plain RAG is good at single-fact questions and **weak on corpus-wide questions**
(every global answer was only "partial"). That is the gap GraphRAG is built to close.

## 8. Limitations and open issues

- The questions were drafted from **abstracts**, so most are easy lookups. 93% on local leaves
  little room to show a gain. A harder set from full text is in the backlog.
- The judge is the **same model** as the answerer and was too strict on two of four spot-checks
  (it marked answers with extra true detail as "partial"). Treat the percentages as rough.
- "Citation numbers valid" only proves the number exists, not that the passage supports the
  sentence. The stronger check is Phase 4.
- Only 25 papers; the real corpus (200 to 300) is not loaded. Results will differ.
- Text cleaning is heuristic: footnotes can land inside a sentence, `multi-hop` can become
  `multihop`, equations and tables are messy, and appendices after References are dropped.
- Licenses are recorded from the Anthology's policy page, not checked paper by paper.
- Section names are kept in `documents.metadata` because the frozen schema has no section
  column (D16). Unit IDs do not include an index version yet (D17).
- Not built yet: the `index_runs` and `run_stages` rows, the daily cost cap
  (`LLM_DAILY_COST_CAP_USD`), and a way to re-ingest after the chunker changes.
- The embedding model is the quantised file; its quality was not compared with the full model.
- Prefect needs FastAPI 0.143.0 (pinned) until Prefect is upgraded.
- The first Docker build downloads about 300 MB of models and is slow on a slow connection.
