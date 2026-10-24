# Phase 3 walkthrough: Communities and global search

## 1. What we built

A way to answer **corpus-wide questions** ("what are the main research directions?") from the
graph, which plain vector RAG answers poorly.

- **Communities**: the 1,545 entities are grouped into **193 communities** in up to three levels,
  by hierarchical Leiden (a standard graph clustering method), with a fixed seed so the same
  graph always gives the same groups.
- **Reports**: every community gets a short report (title, summary, findings with an importance
  score and cited text-unit IDs). 138 are written by `gpt-4.1-mini`; 55 tiny communities
  (fewer than 3 entities) get a stub built without a model.
- **Vector index**: each report is embedded (local model) and stored in Neo4j.
- **Global search**: pick the most relevant reports for a question (**select**), ask the model
  about each batch (**map**), merge the points into one cited answer (**reduce**).
- **Win-rate measurement**: a judge compares global search with the Phase 1 baseline on 20
  corpus-wide questions, in both orders.
- **Review pages** for the owner: 20 communities to rate, 10 judge verdicts to check.

Not built here: local search, router, relate mode, citation support check (Phase 4); API endpoints
and screens (Phase 5). Global search is a command line for now.

## 2. How it works, step by step

1. **Cluster** (`communities.py`). The entity graph is made undirected; an edge weighs the sum of
   its relation weights. Leiden groups the entities (level 0); a group larger than 50 is split
   again (level 1, then level 2). A group small enough is a **leaf** and is not split. An entity
   with no relation becomes its own level-0 community. IDs come from the members, so the same
   result gives the same IDs. Written to Neo4j as `Community` nodes with `IN_COMMUNITY` (one per
   level) and `CHILD_OF`; a checker confirms every entity has a full chain down to a leaf.
2. **Write reports** (`reports.py`), deepest level first. A leaf is described by its most
   connected entities and strongest relationships (each with its text-unit IDs). A split
   community is described by the reports of its children plus its top entities, so no prompt
   is huge. The model must cite only IDs it was shown; other citations are removed, and a report
   with no valid citation left is asked for again (up to 3 tries). Answers are cached by a hash of
   the whole prompt: a repeat is free, and changing one community regenerates only that report
   and the parents that read it.
3. **Embed** (`reports.py`). Report title and summary go through the local bge model into the Neo4j
   vector index `community_report_embedding`. A vector is remade only when the text changes.
4. **Select** (`globalsearch.py`). The question is embedded; the index returns the closest reports
   at the chosen level (default 1, plus unsplit leaves above it, so every entity is covered once);
   stubs are left out; at most 40 are kept.
5. **Map**. Reports are packed into batches of about 6,000 tokens and sent in parallel (8 at a
   time). Each batch returns points with a score from 0 to 100 and the reports behind them;
   score-0 points and points citing nothing valid are dropped. A progress line follows each batch.
   A failed batch does not stop the search; the answer is marked partial.
6. **Reduce**. Points are sorted by score, about 8,000 tokens are used, and the model writes the
   final answer citing reports as `[C1]`. A citation to a report that was not shown is removed.
7. **Judge** (`globaleval.py`). For each question the judge sees the two answers in both orders and
   scores four criteria (comprehensiveness, diversity, empowerment, directness). A criterion is a
   win or a loss only when both orders agree; otherwise it is a tie.

**Example.** Question: "How are human users or human judges involved in the studies in this
corpus?" The closest reports are "Impact of Background Information on User Reliance in QA
Systems", "Human Evaluation and Semantic Methods in QA Assessment" and "A/B Testing in Human
Evaluation for LFQA", and the answer is built from them with `[C1]`-style citations.

## 3. Important files

| File | Job |
|---|---|
| `pipeline/graphlens_pipeline/communities.py` | Leiden clustering, hierarchy checker, Neo4j write |
| `pipeline/graphlens_pipeline/reports.py` | Report prompts, stubs, citation check, cache, embeddings |
| `pipeline/graphlens_pipeline/globalsearch.py` | Select, map, reduce |
| `pipeline/graphlens_pipeline/globaleval.py` | Pairwise judge and win rates |
| `pipeline/graphlens_pipeline/reviewsheets.py` | The owner's review pages |
| `pipeline/graphlens_pipeline/graph_schema/V004`, `V005` | Community constraint and indexes, report vector index |
| `data/eval/v0/global_extra.json`, `REVIEW_EXTRA.md` | The 10 extra global questions (G11 to G20) |
| `data/eval/v0/results/global-phase3.{md,json}` | The win-rate results with every answer and verdict |
| `docs/phases/phase-3-communities/REVIEW_COMMUNITIES.md`, `REVIEW_VERDICTS.md` | For the owner |
| `docs/DECISIONS.md` (D27 to D34) | Why things are the way they are |

## 4. Tools and why

- We used **graspologic-native** (the Rust core of graspologic) for Leiden because it gives the
  same algorithm as the blueprint's graspologic with one small package. We did not choose the
  full graspologic because it pulls in many more heavy packages and the Leiden core is all we
  need (I did not test whether the full package would install here).
- We used **`gpt-4.1-mini`** for reports, map, reduce and the judge because it is cheap and
  follows a JSON schema. We did not choose a bigger model because the cost matters and a
  comparison was not budgeted (D5 stays open). The judge is the same model family as the
  answerer, so the owner checks a sample by hand.
- We used the **local bge model** for report embeddings, as in Phase 1 and 2: free, and the
  question side uses bge's query instruction.
- We used **Neo4j's vector index** for selection, so no new store is needed.
- We used **stub reports without a model** for tiny communities because a model call on one or two
  entities adds cost and little value, and it keeps "every community has a report" true.

## 5. How to run it

PowerShell, in the repository folder, Docker Desktop running, `.env` in place. Steps that call
OpenAI say so.

```bash
docker compose up -d --wait
docker compose run --rm pipeline graph-load                    # the Phase 2 graph, no cost
docker compose run --rm pipeline communities                   # Leiden, no cost
docker compose run --rm pipeline community-reports --dry-run   # cost estimate, nothing spent
docker compose run --rm pipeline community-reports --max-cost-usd 0.75   # about $0.22, cached afterwards
docker compose run --rm pipeline community-embed               # local, no cost
docker compose run --rm pipeline community-quality             # the four gate checks, no cost
docker compose run --rm pipeline global-ask "What are the main research directions in this corpus?"   # about $0.006
```

Evaluation and review pages:

```bash
docker compose run --rm -v "${PWD}/data/eval/v0:/data/eval/v0" pipeline global-eval --dry-run
docker compose run --rm -v "${PWD}/data/eval/v0:/data/eval/v0" -v "${PWD}/data/eval/v0/results:/out" pipeline global-eval --max-cost-usd 1.0 --label phase3
docker compose run --rm -v "${PWD}/data/eval/v0:/data/eval/v0:ro" -v "${PWD}/docs/phases/phase-3-communities:/out" pipeline review-sheets
```

The first full `global-eval` costs about $0.29 and a repeat is free (cached). In Neo4j Browser
(http://localhost:7474) try `MATCH (e:Entity)-[m:IN_COMMUNITY]->(c:Community) WHERE c.level = 0
RETURN c.report_title, count(e) ORDER BY count(e) DESC LIMIT 10`.

**Stop:** `docker compose down` (keeps data) or `docker compose down -v` (deletes data too).

| Problem | Fix |
|---|---|
| `No communities; run the communities command first` | Run `communities` |
| `APITimeoutError` or `APIConnectionError` in a run | The internet dropped; run the same command again (finished work is cached) |
| Image build fails while downloading packages | Run `docker compose build pipeline` again |
| A global answer says "partial" | A map batch failed; ask again |

## 6. How to test it

```bash
docker compose up -d postgres qdrant neo4j
docker compose run --rm --entrypoint pytest pipeline -q -m "not model"     # 305 tests
docker compose run --rm --no-deps --entrypoint ruff pipeline check .
```

Integration tests use their own temporary database and a throwaway `index_version` in Neo4j.
Tests that would call OpenAI use labelled mocks (`ScriptedLlm`, `MockLlm`, `MockJudge`).

## 7. Actual results (2026-10-24, run by Claude on the owner's Windows machine)

- Communities: **193** (level 0: 55, level 1: 117, level 2: 21), 55 stubs; same seed, same
  result; hierarchy checker clean.
- Reports: **193 of 193** have a report (135 new, 3 cached, 55 stubs), no failure, **$0.2224**.
- Gate checks in `quality_checks`: community assignment, communities with a report, valid
  citations and embedding coverage are all **100%**.
- **Global win rate against the plain-RAG baseline, 20 corpus-wide questions** (judge
  `gpt-4.1-mini`, order swapped):

| Criterion | Wins | Ties | Losses | Win rate | 95% interval |
|---|---|---|---|---|---|
| Comprehensiveness | 20 | 0 | 0 | 100% | 84% to 100% |
| Diversity | 20 | 0 | 0 | 100% | 84% to 100% |
| Empowerment | 20 | 0 | 0 | 100% | 84% to 100% |
| Directness | 1 | 16 | 3 | 45% | 26% to 66% |

  Target: at least 60% on comprehensiveness and diversity (met, with the caveats below).
- Without dynamic selection (every level-1 report, first 10 questions): 10 of 10 wins on the
  first three criteria and 40% on directness, the same as with selection. Cost and speed of
  selection are **not yet measured** (see the next section).
- Cost: reports $0.2224, a first report test $0.0062, two test questions $0.0074, evaluation
  $0.2623 plus $0.0297 to redo five items after internet time-outs. **Phase 3 total about $0.53
  of the $2.00 cap.**
- One real question took 11.5 s and cost $0.006.
- Tests: 305 pass; `ruff` clean. CI for this branch has **not run on GitHub yet**.

## 8. Limitations and open issues

- **The 100% is a large effect, but read it with care.** The global answers are about 3.4 times
  longer than the baseline's (median), and judges tend to like longer, more detailed answers.
  The judge is the same model family as the answerer. A plain RAG answer from 6 passages cannot
  cover a corpus-wide question, so a big gap is expected. Directness shows no gain: 16 ties and
  3 losses.
- 20 questions is a small set: one question moves a rate by 5 points, and the interval is
  84% to 100% even at 20 of 20.
- The owner's rating of 20 communities and spot-check of 10 verdicts are **not done yet**.
  Until then the coherence of the communities rests on my reading of a few reports.
- Selection by similarity ranks well but the scores are bunched (0.79 to 0.82), so the threshold
  does nothing and the top 40 does the work.
- The 217-entity community at level 0 mixes several papers; its report is a broad summary.
- Latency and cost per query were measured on one question; the 10-query benchmark (p95 at most
  30 s, at most $0.15 each) waits for the owner's yes (`global-bench`, about $0.08).
- Reports are only as good as the Phase 2 graph (relation precision 0.81, entity-resolution F1
  0.79); some wrong relations will appear in a report.
- A failed model call during an evaluation run needs a re-run (cached work is not paid twice).
- `CITES`, incremental updates and a bigger corpus are still later work.
