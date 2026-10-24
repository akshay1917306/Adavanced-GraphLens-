# Phase 3: Communities and global search

Source: blueprint v1.0 sections 1.2, 2.4 (communities, reports), 2.5 (global search), 4.3, 5.1.

## Goal

Answer **corpus-wide questions** ("what are the main themes?", "how do papers evaluate
open-domain QA?") from the graph, which plain vector RAG cannot do. In Phase 1 the baseline got
**0% correct on the 10 global questions**; this phase closes that gap.

How: group the 1,545 entities into **hierarchical communities**, write a **report** for each
community, and answer a global question by selecting the most relevant reports (**dynamic
selection**), asking the model about each batch (**map**), and merging the points (**reduce**).

## Requirements covered

| ID | Requirement | Plan |
|---|---|---|
| G6 (rest) | Hierarchical communities and a report for each | Hierarchical Leiden with a fixed seed; model-written reports with cited text units |
| G7 | Global search with dynamic community selection, map and reduce, progress events | Select (at most 40 reports), map in parallel batches, reduce; partial failure marked |
| Gate | Entities in a community at every level 100%; communities with a report 100% | New checks in `quality_checks` |
| Exit | Global win rate against the baseline measured | Pairwise LLM judge with swapped order on the global questions; target 60% on comprehensiveness and on diversity |

NFRs: cost control (dry-run estimate, cap, cache keyed by input hash), reproducibility (seed,
prompt and model versions recorded), global search at most $0.15 per query and p95 at most 30 s
with progress updates (blueprint 1.2).

## What the graph looks like (measured 2026-10-24)

1,545 entities, 2,694 edges. **96% of entities (1,489) sit in one connected component**, held
together by hubs (popular datasets such as Natural Questions and HotpotQA, and papers with degree
56 to 75). 25 entities have no edge at all and 10 tiny groups have 2 to 7 entities. So Leiden has
something real to split in the big component, and the tiny pieces need a rule (decision D29).

## Not in this phase

Local search, entity linking, router, relate mode, citation support check (Phase 4); API
endpoints for communities and every screen (Phase 5; here global search is a command line);
incremental updates (v1.5); a bigger corpus (own cost estimate and approval before Phase 4 or 5).

## Decisions to take before the build (Claude's recommendation first)

| ID | Question | Recommendation |
|---|---|---|
| D27 | Which edges feed Leiden? | All edges, as the blueprint says. Check the result; if communities just follow single papers or authors, fall back to content relations only (PROPOSES, USES, EVALUATED_ON, IMPROVES_ON, ADDRESSES, CITES) and attach authors and organizations to their paper's community |
| D28 | Leiden library | `graspologic` (blueprint). It is heavy (scipy, scikit-learn). First step is an install test; fallback `igraph` + `leidenalg` with my own hierarchy |
| D29 | Tiny communities (fewer than 3 entities) | A **stub report** written without a model from the entity descriptions, flagged `is_stub` and left out of global-search selection. Keeps "100% have a report" true and costs nothing |
| D30 | Model for reports, map and reduce | `gpt-4.1-mini` again (cheap, same as Phase 2). A bigger model is not compared (D5 stays open) |
| D31 | Judge and sample size | Pairwise judge `gpt-4.1-mini`, answer order swapped, 4 criteria in one call. It is the same model family as the answerer, so you spot-check 10 verdicts. **Only 10 global questions exist**, which is too few for a firm 60% claim (one question is 10 points). I suggest adding 10 more global questions (I draft from full text, you review, about 30 minutes) |
| D32 | Phase 3 spend cap | $2.00 in total, with a per-run cap and a shown estimate before each paid batch |

## Build steps

1. Install test of the Leiden library in the image (D28), on the real graph.
2. Export the graph and run hierarchical Leiden (seed, maximum cluster size); write `Community`
   nodes with `IN_COMMUNITY` (one per level) and `CHILD_OF`; versioned schema script. Check:
   same seed, same result; every entity at every level.
3. Report inputs: members, key relationships and evidence unit IDs per community (child reports
   when the input is too large); input hash; stub reports (D29).
4. Report generation: strict JSON (title, summary, findings with importance and cited unit IDs);
   cited IDs must come from the community's evidence; cache by input hash; cost cap; **dry-run
   estimate first, your yes, then the paid run**.
5. Embed the reports (local model) and create the Neo4j vector index; gate check "communities
   with a report 100%".
6. Global search: select, map, reduce, progress events, partial failure; command `global-ask`.
7. Evaluation: pairwise runner (swap), baseline answers reused from Phase 1, ablation with and
   without dynamic selection; **estimate first, your yes, then the paid run**.
8. Review sheets for you: 20 sampled communities (coherence 1 to 5) and 10 judge verdicts.
9. Quality report extension, tests, docs, WALKTHROUGH, README, CI.

## Cost (assumptions, to be replaced by the dry-run measurement)

- Reports: about 150 to 300 communities, roughly $0.002 each with `gpt-4.1-mini`, so **$0.3 to
  $0.8** with retries.
- Global search: about $0.02 per query (40 reports, 4 map calls, 1 reduce). 10 questions, with
  and without dynamic selection: **$0.3 to $0.8**.
- Pairwise judging: **under $0.15**. Small live tests while building: **about $0.2**.
- Expected total **$0.8 to $1.8**; the cap in D32 is $2.00. Embeddings, Leiden and the Neo4j
  work are local and free. These are estimates, not measurements.
