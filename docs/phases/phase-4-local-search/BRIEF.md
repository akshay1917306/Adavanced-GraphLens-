# Phase 4: Local search, router, relate mode and citation check

Source: blueprint v1.0 sections 1.2, 2.6 (query pipeline), 2.10 (evaluation), 5.1.

## Goal

Answer **specific, multi-hop questions** ("Which methods that improve on FiD were evaluated on
Natural Questions?") by following the graph, show **how two things are connected**, **choose the
right mode automatically**, **check every citation**, and **refuse or ask** when the evidence is
thin. After Phase 3 only corpus-wide questions use the graph; local questions still use plain RAG.

## Requirements covered

| ID | Requirement | Plan |
|---|---|---|
| G9 | Local search: entity linking, bounded graph expansion, context assembly | Link question to entities, expand 2 hops with a fixed query, score with personalized PageRank, assemble a budgeted context, answer with `[T]` `[E]` `[C]` citations |
| G11 | Baseline vector mode for simple lookups | Exists since Phase 1; add the optional rerank (top 20 to 5) |
| G12 | Router with manual override | A small model plus rules chooses local, global, relate or baseline; low confidence runs local and says so |
| G13 | Relate mode | Link two entities, find up to 3 paths of at most 4 hops, explain with evidence for every hop |
| G16 | Citation check | Every cited ID must exist in the retrieved context; sentences naming entities that are not in the context are flagged; result `verified`, `warning` or `not_checked` |
| G17 | Refuse or clarify | Refuse when no seed entity is similar enough or the evidence is thin; ask which one when an entity is ambiguous |

Targets (blueprint 1.2): local correctness at least 75% and at least 15 points above baseline;
citation precision at least 90%; refusal accuracy at least 90% on unanswerable questions; local
query at most $0.03 and p95 at most 8 s. Phase exit: "local benchmark meets the target over
baseline".

## A problem to settle first

The local questions we have (30, from Phase 1) were drafted from abstracts, and the plain
baseline already gets **93%** of them right. "At least 15 points above baseline" cannot be shown
on a set where the baseline is at 93%. The blueprint expects a harder set (50 multi-hop
questions). Decision D35 below.

## Not in this phase

API endpoints, streaming and every screen (Phase 5; here everything is a command line); users,
rate limits, access control (Phase 6); incremental updates (v1.5); a bigger corpus.

## Decisions to take before the build (Claude's recommendation first)

| ID | Question | Recommendation |
|---|---|---|
| D35 | Local benchmark | Build a **harder local set of 30 multi-hop questions from the full text** of the papers (answers need 2 or more text units, usually 2 papers), reviewed by you (about 1 hour 30 minutes). Keep the 30 easy ones as a second set. The 15-point claim is measured on the hard set; I also report the easy set, where the ceiling is 100% |
| D36 | Graph scoring | Personalized PageRank in numpy (already installed). No new package and no Neo4j plugin (Community has no graph algorithms) |
| D37 | Router | Rules first (they are free and explainable), a `gpt-4.1-mini` call for the rest, confidence under 0.6 runs local. Measured on a labeled set of questions (D38) |
| D38 | New evaluation sets | 10 unanswerable questions (about things outside the 25 papers), 20 entity pairs for relate mode, and mode labels for every question we have. I draft all of them; you review (about 1 hour in total) |
| D39 | Citation check | Two parts. Automatic: every `[T]` `[E]` `[C]` exists in the context, unknown entities in a sentence are flagged. Support check (does the passage really back the claim): a judge on every benchmark answer, and you spot-check 10 |
| D40 | Models and spend | `gpt-4.1-mini` everywhere (D30). **The owner asked to keep OpenAI spend low**, so Phase 4 cap is **$0.80** (not $2.00), with a shown estimate before every paid batch. Building and testing use mock models only; real calls are limited to a few smoke tests and one approved evaluation (see Cost) |

## Build steps

1. Sanitiser (length, keys, tokens, emails) and entity linking (vector index plus alias match).
2. Expansion with a fixed Cypher template, personalized PageRank, top 60 nodes.
3. Context assembly with the token budget (45% text units, 25% entities and relationships, 20%
   community reports, 10% reserved) and the `[T]` `[E]` `[C]` labels.
4. Local answer, refusal and clarify rules, the automatic citation check.
5. Relate mode (up to 3 paths, 4 hops, evidence per hop, nearest shared communities if none).
6. Router and one `ask` command that picks the mode; optional rerank in baseline mode.
7. The new evaluation sets (D35, D38), drafted by me and reviewed by you.
8. Evaluation, kept small: the ablation of each step (entity linking, expansion, PageRank,
   community reports) is measured **without any model call** (how many of the evidence text
   units end up in the context); model answers are generated only for baseline, local without
   community reports, and full local, on the hard set; plus refusal accuracy, relate path
   correctness (checked against the graph, no model), router accuracy (rules first) and a
   sampled citation-support check. **Estimate first, your yes, then the paid run.**
9. Tests, docs, WALKTHROUGH, README, CI and the A to J report.

## Cost (assumptions, to be replaced by a dry run)

The owner asked to keep the OpenAI spend low, so the plan is built around free measurements.

- **Free (no model call):** entity linking, graph expansion, PageRank, context assembly, the
  citation check of IDs, path finding, router rules, and the ablation of each retrieval step
  (share of the evidence text units found in the context). All tests use labelled mock models.
- **Paid, small:**
  - one local answer is about 6,000 tokens in and 800 out with `gpt-4.1-mini`, roughly
    **$0.004 to $0.006**;
  - model answers for 3 configurations on the 30 hard questions: about **$0.45**;
  - correctness judge on those answers (about 60 short calls): about **$0.05**;
  - refusal test (10 questions): about **$0.05**; citation-support judge on a sample of 20
    answers: about **$0.04**; router model calls for the unclear questions only: under **$0.01**;
  - a few live smoke tests while building (about 10 calls): about **$0.05**.
- Expected total **$0.6 to $0.75**, against the **$0.80** cap in D40. Every cost is cached, so
  repeating a run is free. These are estimates, not measurements; the dry run replaces them.
- **OpenAI monthly limit:** this month's spend is about $3.3 (Phase 1 $0.05, Phase 2 $2.40,
  Phase 3 $0.69, small extras). With about $0.7 more it stays under $5. A limit of $5 in the
  OpenAI dashboard is enough; nothing needs to be raised.
