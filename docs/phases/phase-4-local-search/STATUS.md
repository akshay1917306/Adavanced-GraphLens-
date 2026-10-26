# Phase 4 status

Last updated: 2026-10-26

## State

**Built and evaluated (paid run done, $0.27). Waiting for owner review of the question sets, the WALKTHROUGH and approval.** Local branch `phase-4/local-search`, branched from `main` at ce6f4de (tagged
`phase-3`, merged as PR #4). Nothing from Phase 4 is pushed.

## Completed

- Phase 3 checkpoint finished: PR #4 merged, CI green on the branch commit and on `main`, tag
  `phase-3` pushed and verified (remote and local both point to ce6f4de).
- Plan approved by the owner in its lean form (D35 to D40, cap **$0.80**, "do not use much
  OpenAI"), 2026-10-26.
- Step 1 (`linking.py`): sanitiser (4,000 characters, keys, tokens, passwords, emails redacted)
  and entity linking by name match plus the vector index; ambiguous names reported; each seed has
  a weight. A vector score of 0.79 separates in-corpus questions (at least 0.81) from
  out-of-corpus ones (at most 0.77) on 40 + 8 questions tried.
- Step 2 (`localgraph.py`): one fixed parameterised expansion query (ontology relation types
  only, never the community links), numpy personalized PageRank, best 60 nodes.
- Step 3 (`localcontext.py`): 8,000-token context split 45% text units, 25% entities and
  relations, 20% reports, 10% left empty; labels `[T]` `[E]` `[C]`; angle brackets neutralised.
- Step 4 (`localanswer.py`): refuse (no entity close enough, thin evidence), clarify (two entities
  of one type share a name), one model call, citation check (`verified`, `warning`,
  `not_checked`).
- Step 5 (`relate.py`): two entities, up to 3 shortest paths of at most 4 hops, evidence per hop,
  nearest shared communities when there is no path.
- Step 6 (`router.py`): rules first, a small model only when unsure, under 0.6 runs local with a
  note, manual override. Rules only: 46 of 50 acceptable (92%). `ask-auto` runs the chosen mode.
  The optional rerank for baseline mode is **not built** (a new model download; deferred).
- Step 7: new question sets in `data/eval/phase4/`: 30 hard multi-hop questions (every quote
  verified), 10 unanswerable, 20 relate pairs with a known path; review pages in this folder.
- Step 8 (code): `localeval.py` and `local-eval`. **Dry run: about $0.36 (about $0.51 with
  margin) against the $0.80 cap.** Not run yet.
- Real model calls so far, all small tests: three local questions ($0.0034, $0, $0.0031) and one
  relate explanation ($0.0016), about $0.01 in total. Phase 4 spend so far: about $0.01.
- Tests: 394 pass; `ruff` clean (locally in Docker). CI has not run for this branch.

## What the free measurements already show

On the share of gold evidence units that reach the model (no model call):

| | easy set (30) | hard set (30, held out) |
|---|---|---|
| plain RAG, 6 passages | 88% | 52% |
| graph reach after linking only | 93% | 75% |
| after expansion (2 hops) | 97% | 95% |
| after PageRank | 97% | 95% (no gain) |
| text units really shown in the 8,000-token context | 93% | 57% |

Reading it: the graph reaches almost all the evidence, but the context has room for only about 11
passages, so on the hard set the shown evidence is only a little above plain RAG. A first version
of the passage ranking showed less than plain RAG (37% on the hard set); it was fixed on the easy
questions only (citation weight 0.25 and the 6 best plain-search hits placed first) and then
checked once on the hard set. PageRank added nothing on either set.

## Paid evaluation result (2026-10-26, `data/eval/phase4/local-eval-phase4.json`, cost $0.2671)

| system (30 hard questions) | correct | partial | incorrect | share correct (95% interval) |
|---|---|---|---|---|
| plain RAG baseline | 16 | 10 | 4 | 0.53 (0.36-0.70) |
| local search | 21 | 7 | 2 | 0.70 (0.52-0.83) |
| local without reports | 21 | 7 | 2 | 0.70 (0.52-0.83) |

- Local vs baseline, paired: 9 wins, 19 ties, 2 losses. The intervals overlap, so this is a
  encouraging sign on 30 questions, not proof. Judge is the same model family as the answerer.
- Community reports add nothing on these questions (identical to no-reports).
- Local answers are slower (5.2 s vs 2.4 s mean).
- Citation support: 122 of 124 sampled citations supported (98.4%, 20 answers).
- Refusal: 8 of 10 unanswerable refused (80%); U09 and U10 were answered anyway (below a 90% bar if one is set; to be looked at).
- Relate: 20 of 20 paths found, 20 of 20 right length; only 11 of 20 explanations passed the citation check as `verified`.
- Router with the model on unsure questions was not run separately (rules only: 46/50).

## Blockers

None.

## Decisions waiting for the owner

- Review of the new question sets: `REVIEW_LOCAL_HARD.md`, `REVIEW_RELATE.md`,
  `REVIEW_UNANSWERABLE.md` (about 2 to 2.5 hours; it can happen after the run, a changed question
  is simply run again).

## Exact next action

Fill CHECKLIST, write WALKTHROUGH, update README and DECISIONS (D35-D40), look at U09/U10 and the 9 unverified relate explanations, send the A to J report. No more paid runs without a yes.

## Notes for the next session

- Run everything through Docker; repository folder:
  `C:\Users\ACER\Downloads\Advanced GraphLens\Adavanced-GraphLens-`.
- `docker compose up -d --wait` starts the stack; the Phase 3 commands rebuild the community
  layer from cache at no cost.
- Git Bash rewrites `/out`-style paths and breaks on long here-documents with quotes; use
  PowerShell for `docker compose run -v ...` commands and write long scripts to a file first.
- The network to PyPI, GitHub and OpenAI drops now and then; finished work is cached, so run the
  same command again.
