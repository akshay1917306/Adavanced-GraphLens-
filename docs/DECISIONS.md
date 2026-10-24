# Decision log

Closes the open decisions in blueprint v1.0 section 5.3. A decision that needs
measurement is assigned to the phase that measures it. Changes to frozen decisions
go through an ADR (see `docs/adr/`).

| # | Decision | Outcome | Status | Date |
|---|---|---|---|---|
| D1 | Phase plan | Follow the blueprint roadmap (section 5.1): phases 0 to 8. The owner's earlier generic list (landing page, auth, ACL...) came from a different project and is not used | Owner said "start the phase" after this was proposed; please confirm at Phase 0 review | 2026-10-21 |
| D2 | LLM provider | OpenAI, see ADR-0001 | Provider chosen by owner; ADR text awaiting review | 2026-10-21 |
| D3 | Corpus and domain | Research literature. Phase 0 uses a 10-document **synthetic** fixture. Real corpus: question answering (QA) methods and benchmarks from the ACL Anthology, CC BY papers only, 20 to 30 for development, 200 to 300 later after a cost estimate | Decided by owner | 2026-10-23 |
| D4 | Ontology scope | 6 entity types, 8 predicates (blueprint default), `ontology/research_v1.yaml` | Decided | 2026-10-21 |
| D5 | Extraction model | `LLM_MODEL_SMALL` first; compare on a 5% sample in Phase 2, upgrade if precision < 0.80 | Method decided, measured in Phase 2 | 2026-10-21 |
| D6 | Gleaning passes | Compare 0 and 2 on the sample in Phase 2 | Method decided, measured in Phase 2 | 2026-10-21 |
| D7 | Community level for global search | Default level 1; test 0 and 2 in Phase 3 | Decided (default) | 2026-10-21 |
| D8 | Neo4j edition | Community 5.26 (LTS line), self-hosted in Docker | Decided | 2026-10-21 |
| D9 | Embeddings | Local bge-base-en-v1.5, 768 dimensions (Phase 1) | Decided | 2026-10-21 |
| D10 | Judge protocol | `LLM_MODEL_MAIN`, answer order swapped, 10% human spot check (ADR-0001) | Decided | 2026-10-21 |
| D11 | Sign-in method | Deferred to v1.5 | Deferred | 2026-10-21 |
| D12 | Hosting | Deferred to Phase 7 | Deferred | 2026-10-21 |
| D13 | Phase tags | Tag `phase-N` on the approved merge commit (the blueprint does not name tags) | Proposed | 2026-10-21 |
| D14 | Python packaging | `uv` with a lock file; exact versions in `api/pyproject.toml` | Decided | 2026-10-21 |
| D15 | PDF text extraction | **pypdf** (BSD-3). Tested on 5 corpus papers on 2026-10-23: pypdf kept normal word spacing (about 0.13 spaces per character) and read the two columns in order. pdfminer.six (MIT) glued words together (about 0.002 spaces per character), also with a tuned setting. PyMuPDF rejected because of its AGPL license. pypdf output still needs cleaning: ligatures (NFKC), end-of-line hyphens, page numbers, running headers, and cutting at References | Decided, re-measure if a paper extracts badly | 2026-10-23 |
| D16 | Where section names are stored | The blueprint wants section metadata per text unit (G2) and puts `section` in the Qdrant payload (4.5), but the Postgres `text_units` table has no section column. To keep the frozen schema unchanged, Phase 1 stores the section of every unit in `documents.metadata` as `unit_sections` (a list indexed by unit ordinal). Qdrant payloads will read it from there. If a real column is wanted, raise a Change Request | Decided, reversible | 2026-10-23 |
| D17 | Text unit IDs | `u_<first 12 characters of the document content hash>_<4-digit ordinal>`. The same file and chunker version always give the same IDs. The blueprint says IDs include the index version (4.1); index versions start in Phase 2, so this is revisited there | Decided for Phase 1, revisit in Phase 2 | 2026-10-23 |
| D18 | Text unit size | **450 tokens, 75 overlap** (was about 600 and 100) so units fit the 512-token input of bge-base-en-v1.5. See CR-0002. Measured: 36% of units were too long before, 0.4% after | Decided by owner (option B) | 2026-10-23 |
| D19 | Embedding runtime and Qdrant layout | Dense: `BAAI/bge-base-en-v1.5` through **fastembed** (ONNX, int8-quantised file, about 210 MB, MIT; the unquantised model is about 440 MB and needs PyTorch). Sparse: `Qdrant/bm25` through fastembed, with the IDF modifier in Qdrant. Both run locally and cost nothing. Collection `units_qa_v0_baseline_1` (name rule from blueprint 4.5); the alias `units_live` points at it for now. Vectors and a small payload only; text stays in Postgres. `qdrant-client` is pinned to 1.15.1 to match the server v1.15.4. Quantisation can lower quality slightly; compare against the unquantised model if retrieval looks weak | Decided | 2026-10-24 |
| D20 | Evaluation set v0 | 30 local and 10 global questions drafted by Claude from the abstracts of the 25 development papers. Every reference answer carries exact evidence quotes that a script checks against the corpus text. The set counts as an answer key only after the owner reviews it. This is the development set; the blueprint benchmark (50 local, 20 global, 20 relate, 10 unanswerable) is built later on the real corpus | Draft, owner review pending | 2026-10-24 |
| D21 | Prefect and the FastAPI pin | Prefect **3.8.8** (Apache-2.0) runs the ingest and embed stages as a flow with retries. It adds 78 packages. It needs FastAPI 0.139 or newer, while FastAPI 0.156 and newer break its server code, so the pipeline pins FastAPI to **0.143.0** until Prefect is upgraded. Prefect analytics are disabled. Resume works because the stages are idempotent; Prefect run records are temporary | Decided | 2026-10-24 |
| D22 | Front-matter text unit | Keep title, authors and affiliations as the first text unit of each paper (email and web lines removed) so `AUTHORED_BY` and `AFFILIATED_WITH` have evidence. Chunker version 3. The corpus was re-ingested (751 units), re-embedded into `units_qa_v0_baseline_2`, and the evaluation evidence remapped by quote and loaded as set version 2. See CR-0003. `CITES` is left for the backlog | Decided by owner (option A) | 2026-10-24 |
