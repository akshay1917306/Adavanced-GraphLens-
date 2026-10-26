# Phase 4 walkthrough: Local search, relate and router

## 1. What we built

Answers for **specific questions** from the graph, with cited evidence.

- **Local search**: link the question to entities, expand 2 hops, rank, build a labeled context
  (`[T]` text units, `[E]` entities and relations, `[C]` community reports), one model call.
- **Relate mode**: "how are A and B connected?" gives up to 3 shortest paths (at most 4 hops) with
  evidence for every hop; if no path exists, the nearest shared communities.
- **Router**: rules first; a small model only when unsure; below 0.6 confidence runs local and
  says so; the mode can be forced.
- **Citation check**: every label must exist in the context; sentences naming unknown entities are
  flagged. Result: `verified`, `warning` or `not_checked`.
- **Refusal and clarify**: refuse when no entity is close enough or evidence is thin; ask when two
  entities of the same type share a name.

Not built: baseline rerank (deferred); API and screens (Phase 5).

## 2. How it works

1. `linking.py` cleans the question (4,000 characters, keys, tokens, emails removed), matches names
   and the entity vector index (score at least 0.79), at most 5 seeds.
2. `localgraph.py` runs one fixed parameterised Cypher query over ontology relations only
   (2 hops, 200 candidates), then PageRank in numpy keeps 60 nodes.
3. `localcontext.py` fills 8,000 tokens (45/25/20, 10% free); the 6 best plain-search passages go first.
4. `localanswer.py` asks the model once, then checks the citations.
5. `relate.py` and `router.py` as above. No model ever writes Cypher.

## 3. What we measured

| | result |
|---|---|
| Evidence reaching the model, hard set: plain RAG, linking, expansion, PageRank | 52%, 75%, 95%, 95% |
| Evidence actually shown in the context, hard / easy | 57% / 93% |
| Correct on 30 hard questions: local, local without reports, baseline | 70%, 70%, 53% |
| Local vs baseline | 9 wins, 19 ties, 2 losses |
| Citation support (judge) | 122 of 124 |
| Refusal on 10 unanswerable | 8 (U09, U10 answered) |
| Relate on 20 pairs | 20 paths, 20 right length, 11 verified |
| Router (rules only) | 46 of 50 acceptable |
| Cost of the paid run | $0.267 (total Phase 4 about $0.28 of $0.80) |

## 4. Honest limits

- 70% is below the 75% target. The graph reaches 95% of the evidence, but the context holds only
  about 11 passages, so the shown evidence is the bottleneck.
- 30 questions only; intervals overlap with the baseline. Judge is the same model family.
- PageRank and community reports gave no measurable gain.
- U09 matched the generic dataset name "accuracy"; U10 matched an entity named "claude". A
  stricter match for generic or single-word names is a possible fix (not done).
- Why 9 of 20 relate explanations were not `verified` was not diagnosed (not stored; finding out
  costs a few cents).
- Not measured: p95 latency, easy-set paid correctness, router model step. Baseline rerank not built.
- Question sets were drafted by Claude; the owner review is pending.

## 5. How to run

```bash
docker compose up -d --wait
docker compose run --rm pipeline local-ask "your question"
docker compose run --rm pipeline relate "How is X connected to Y?"
docker compose run --rm pipeline ask-auto "your question"
```
