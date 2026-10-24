# Phase 2 walkthrough: Extraction and graph

## 1. What we built

A **knowledge graph** of the 25 development papers, stored in Neo4j, where every node and edge
points back to the passages that support it.

- **Ontology** (`ontology/research_v2.yaml`): the allowed entity types (Paper, Author, Method,
  Dataset, Task, Organization) and relation names (`PROPOSES`, `USES`, `EVALUATED_ON`,
  `IMPROVES_ON`, `ADDRESSES`, `AUTHORED_BY`, `AFFILIATED_WITH`, `CITES`) and which types each
  relation may join.
- **Extraction**: for each of the 751 text units, `gpt-4.1-mini` lists the entities and
  relations it sees, as strict JSON. A second check drops anything outside the ontology.
- **Entity resolution**: "DPR", "Dense Passage Retrieval" and "Dense Passage Retrieval (DPR)"
  become one entity, with the other spellings kept as aliases and every decision stored.
- **Neo4j load**: versioned schema scripts, nodes with source passages, edges with evidence
  passages, and one vector per entity in a vector index.
- **Quality report**: automatic checks on the real graph, stored in `quality_checks`.
- **Labeled samples**: 30 text units (182 relations) and 110 entity pairs to measure how
  accurate extraction and resolution really are.

Not built here: communities and reports (Phase 3), graph search, router, answers from the
graph, web interface.

## 2. How it works, step by step

1. **Front matter kept** (CR-0003). Each paper keeps its title, authors and affiliations as one
   text unit, so `AUTHORED_BY` and `AFFILIATED_WITH` have evidence. Email and web addresses
   are removed.
2. **Extract** (`extract.py`). The prompt shows one passage inside tags and says the passage is
   data, not instructions. The answer must match a JSON schema built from the ontology. Up to
   3 tries per unit. Answers are cached in Postgres by (passage hash, prompt version, model,
   ontology fingerprint), so repeating a run costs nothing. A cost cap stops a run cleanly.
3. **Second check** (`parse_answer`). Unknown types, unknown relation names, relations whose
   ends are not extracted entities, and relations the ontology does not allow are dropped and
   counted.
4. **Resolve** (`resolve.py`). Names are grouped when they differ only by case, hyphens,
   spaces or a plural. "Long Form (ACR)" links the acronym. Close pairs (spelling, acronym,
   embedding) become candidates. Hard rules block merging different numbers, size words or
   negations. Only a name plus a generic word ("KG-FiD" and "KG-FiD model") merges without
   asking. The gray zone goes to the model, and then a **guard** (`merge_veto`) overrules
   any "same" answer unless one name is an acronym of the other or they differ only by generic
   words, plurals or word order.
5. **Load** (`graphstore.py`). Schema scripts `V001` to `V003` run once (their checksums are
   stored). Nodes and edges are written with fixed query templates and parameters only; labels
   and relation names come from the ontology and are checked first. Loading twice gives the
   same graph. Entities that have no relation and were mentioned once are left out (D25).
6. **Check** (`quality.py`). Reads Neo4j and Postgres and stores the checks.
7. **Label** (`labelsets.py`). Draws repeatable samples; a person other than the extraction
   model gives each item a label; the scorer weights each stratum back to its full size.

**Example.** The passage "We use DPR to retrieve passages" in a paper about KG-FiD gives
`KG-FiD USES DPR retriever`. The edge stores the passage ID, so you can open the text that
supports it.

## 3. Important files

| File | Job |
|---|---|
| `ontology/research_v1.yaml`, `research_v2.yaml` | Allowed types and relations (v2 widens only `USES`, D24) |
| `pipeline/graphlens_pipeline/extract.py` | Prompt, schema, second check, cache, cost cap |
| `pipeline/graphlens_pipeline/resolve.py` | Grouping, candidates, rules, model judge, guard, decisions |
| `pipeline/graphlens_pipeline/graphstore.py` | Neo4j schema and idempotent load |
| `pipeline/graphlens_pipeline/graph_schema/V00*.cypher` | Versioned constraints and indexes |
| `pipeline/graphlens_pipeline/quality.py` | The gate checks |
| `pipeline/graphlens_pipeline/labelsets.py` | Samples, scoring |
| `pipeline/graphlens_pipeline/runs.py` | `index_runs` and `run_stages` records |
| `data/eval/labels/v0/` | The labeled samples and review pages |
| `docs/phases/phase-2-extraction/QUALITY.md` | The latest quality report |
| `docs/DECISIONS.md` (D22 to D25), `docs/adr/CR-0003-*.md` | Why things are the way they are |

## 4. Tools and why

- We used **`gpt-4.1-mini`** for extraction and the resolution judge because it is cheap
  ($0.40 and $1.60 per million tokens in and out) and follows a JSON schema. We did not choose a
  bigger model because the full extraction of 751 units cost $0.77 with it and the budget cap
  was $3. A bigger model was **not compared**; the choice (D5) is still open until the labels
  are reviewed.
- We used **no gleaning** (extra passes for missed items). Two extra passes gave 4% more
  entities for 63% more cost ($1.25 against $0.77). Whether they add correct items is **not
  measured** (D6 stays open).
- We used **local embeddings** (the same bge model as Phase 1) for entity names and
  descriptions. We did not choose a paid embedding model because it adds cost for no known gain.
- We used the **official `neo4j` Python driver** (5.28.2) with fixed query templates. We did not
  choose a Cypher-writing model, because model-written queries are a security risk.
- We used **Neo4j Community** (blueprint choice). It has a vector index, which is all Phase 2 needs.

## 5. How to run it

PowerShell, in the repository folder, Docker Desktop running, `.env` in place. Steps that call
OpenAI say so.

```bash
docker compose up -d --wait                                  # Postgres, Neo4j, Qdrant, Redis, API
docker compose run --rm pipeline index                       # Phase 1 data, if not loaded yet
docker compose run --rm pipeline extract-estimate            # cost estimate, nothing spent
docker compose run --rm pipeline extract --sample 1 --gleaning 0 --index-version idx2-full-g0 --max-cost-usd 1
docker compose run --rm pipeline resolve                     # small model cost, cached answers are free
docker compose run --rm pipeline graph-load                  # no cost
docker compose run --rm -v "${PWD}/docs/phases/phase-2-extraction:/out" pipeline quality-report --out /out/QUALITY.md
```

The `extract` line costs about **$0.77** the first time and **$0** when the cache is warm (as it
is on the owner's machine now). Do not run it without checking the estimate.

**See the graph:** open http://localhost:7474 and sign in as `neo4j` with `NEO4J_PASSWORD` from
`.env`. Try:

```
MATCH (m:Method)-[r:EVALUATED_ON]->(d:Dataset) RETURN m, r, d LIMIT 25
MATCH (e:Entity) RETURN e.type AS type, count(*) AS n ORDER BY n DESC
MATCH (a:Entity)-[r]->(b:Entity) RETURN a.name, type(r), b.name, r.evidence_unit_ids LIMIT 10
```

The last query shows the passage IDs behind each edge. The vector index (`entity_embedding`) is
queried with a 768-number list, as in `tests/test_graphstore.py`.

**Stop:** `docker compose down` (keeps data) or `docker compose down -v` (deletes data too).

| Problem | Fix |
|---|---|
| `Only N of 751 units are extracted; run extract first` | Run the `extract` line (it resumes from the cache) |
| `Graph load refused: ... no source` | An entity or edge has no passage ID; this is a bug, report it |
| Image build fails while downloading packages | The connection dropped; run `docker compose build pipeline` again |
| `NEO4J_PASSWORD` error | Set it in `.env` |

## 6. How to test it

```bash
docker compose up -d postgres qdrant neo4j
docker compose run --rm --entrypoint pytest pipeline -q -m "not model"     # 250 tests
docker compose run --rm --no-deps --entrypoint ruff pipeline check .
```

Integration tests use their own temporary database, Qdrant collections and a throwaway
`index_version` in Neo4j. Tests that would call OpenAI use labelled mocks (`FakeLlm`,
`ScriptedLlm`, `Judge`).

## 7. Actual results (2026-10-24, run by Claude on the owner's Windows machine)

- Extraction, 751 units, ontology v2, `gpt-4.1-mini`, no gleaning: **4,591 entity mentions and
  3,611 relations**, cost $0.77. The second check dropped 573 proposed relations (196 with an
  end that was not an extracted entity, 377 whose types the relation does not allow).
- Resolution: 4,591 mentions became **1,842 entities** (80 automatic merges, 58 model merges that
  passed the guard, which was loosened for symbols in D26). The first model pass said "same" 164 times; I read the first 100 and about 15
  to 20 were wrong, so the guard was added. The merges that remain were all read by me.
- Neo4j: **1,545 entities and 2,694 relations**, all embedded. 297 entities with no relation that
  were mentioned once were left out (D25).
- Total OpenAI spend in Phase 2: about **$2.40** of the $3 cap.
- Quality checks (`QUALITY.md`): schema validity 100%, node provenance 100%, edge evidence 100%,
  ontology conformance 100%, embedding coverage 100%, duplicate proxy 2.7%, orphan rate 1.6%
  (**17.5% before** the lonely entities were left out, a miss against the 10% target).
- Accuracy from the labeled samples (I drafted the labels, the owner confirmed all of them):
  relation precision **0.81** (target 0.80, narrow; 0.72 to 0.83 depending on the 20 unsure
  items); entity-resolution precision 1.00, recall 0.65, **F1 0.79** (target 0.85, a miss).
- Tests: 250 pass; `ruff` clean. CI for this branch has **not run on GitHub yet**.

## 8. Limitations and open issues

- Only I drafted the labels and the owner confirmed them without changing any, so the labels
  have one author in practice. 20 relations and 16 pairs are "unsure" and are left out.
- The resolver is strict by design (a wrong merge hurts more than a missed one), so recall is
  low: pairs like `Step Verifier (Vs)` and `step verifier Vs` stay apart. Recall only covers
  pairs the resolver looked at; names that never became a pair are not counted.
- The wrong relations follow patterns: baselines or related work recorded as "USES", ablation
  variants recorded as used, datasets used as a knowledge source recorded as "EVALUATED_ON".
  Fixing them means a better prompt (Phase 3 work, costs money).
- 17.5% of extracted entities had no relation. Leaving the single-mention ones out hides that
  in the graph, but the original number is stored as `orphan_rate_before_pruning`.
- Gleaning and model choice (D5, D6) are not decided because precision of the extras is not
  measured.
- `CITES` edges (46) come from the model reading in-text citations; reference-list parsing is in
  the backlog.
- The `idx2-full-g0` and `idx2-full-g2` run records stay `running` until the owner approves the
  quality gate. Communities are Phase 3.
- Only 25 papers. A 200 to 300 paper corpus needs its own cost estimate and approval.
- The daily cost cap (`LLM_DAILY_COST_CAP_USD`) is still not enforced by code.
