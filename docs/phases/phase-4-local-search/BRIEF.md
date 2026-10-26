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
| D40 | Models and spend | `gpt-4.1-mini` everywhere (D30). Phase 4 cap **$2.00** with a shown estimate before every paid batch |

## Build steps

1. Sanitiser (length, keys, tokens, emails) and entity linking (vector index plus alias match).
2. Expansion with a fixed Cypher template, personalized PageRank, top 60 nodes.
3. Context assembly with the token budget (45% text units, 25% entities and relationships, 20%
   community reports, 10% reserved) and the `[T]` `[E]` `[C]` labels.
4. Local answer, refusal and clarify rules, the automatic citation check.
5. Relate mode (up to 3 paths, 4 hops, evidence per hop, nearest shared communities if none).
6. Router and one `ask` command that picks the mode; optional rerank in baseline mode.
7. The new evaluation sets (D35, D38), drafted by me and reviewed by you.
8. Evaluation with ablations (baseline, plus entity linking, plus expansion, plus PageRank, plus
   community reports), refusal accuracy, relate path correctness, router accuracy, citation
   support. **Estimate first, your yes, then the paid run.**
9. Tests, docs, WALKTHROUGH, README, CI and the A to J report.

## Cost (assumptions, to be replaced by a dry run)

- One local answer: about 8,000 tokens in and 1,200 out with `gpt-4.1-mini`, roughly **$0.005 to
  $0.01**, plus the router call (under $0.001).
- Evaluation: 5 configurations on 30 hard questions plus the easy set, a correctness judge and a
  citation-support judge: roughly **$1.0 to $1.6**. Refusal, relate and router runs: under $0.2.
  Small live tests while building: about $0.2.
- Expected total **$1.2 to $2.0**, against the $2.00 cap in D40. Entity linking, graph work,
  PageRank and embeddings are local and free. These are estimates, not measurements.
- **OpenAI monthly limit:** this month's spend is already about $3.3 (Phase 1 $0.05, Phase 2
  $2.40, Phase 3 $0.69, small extras). Phase 4 could take it past $5, so please set the limit in
  the OpenAI dashboard to at least $8 before the paid evaluation, or tell me to stay lower.
