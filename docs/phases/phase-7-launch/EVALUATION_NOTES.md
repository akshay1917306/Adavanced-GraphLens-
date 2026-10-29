# Reading the final evaluation

The numbers are in [docs/EVALUATION.md](../../EVALUATION.md), written by the script from
`data/eval/final/final-eval.json` (2026-10-29, cost $0.3206, estimate was $0.41). This page is the
human reading of them. Three targets were **missed**; they are not hidden anywhere.

## The three misses

**1. Local correctness on the hard set: 70% (21 of 30), target 75%.** Exactly the Phase 4 result
(21 of 30), although the code changed in Phase 7: the fixes of this phase concern refusals and
checks, not the answers of answerable questions, and the measurement confirms that nothing got
worse. The 95% interval is 52% to 83%, so the target is neither clearly missed nor reachable with
this evidence. Phase 4's analysis still holds: the graph reaches 95% of the gold passages but only
about 57% of them fit into the 8,000-token context, and 12,000 tokens did not help clearly (D68).

**2. Gap over plain RAG: +13.3 points, target +15.** Local 21 of 30, plain RAG 17 of 30 (57%; it was
16 of 30 in Phase 4). The gap is 1.7 points short, which is half a question: it is inside the noise
of a 30-question set judged by the same model family. Local search is better on the hard set in both
runs, but "at least 15 points" is not shown.

**3. Time per local answer, p95: 10.3 s, target 8 s.** Median 5.4 s, 10 of 60 answers took longer than
8 s, the slowest 26.6 s (question M29: the same number of tokens and the same cost as its neighbours,
so that was waiting for the provider). Plain RAG averaged 2.2 s. Where the time goes: retrieval about
0.5 s, the rest is one model call that writes up to 250 words. Ideas, **not done**: a shorter answer
limit (would need a new correctness run), streaming the answer so the first words appear at once
(planned for v1.5), a second server process for the retrieval. These are one-at-a-time times; ten
people at the same moment are slower (LOAD_TEST.md).

## Things that went well, with their limits

- **Citation support 99.1%** (114 of 115 claims in 20 answers): the judge is the same model family,
  and it checks that a cited passage backs the claim, not that the claim is the best answer.
- **Router 97%** (97 of 100) with its model step and the entity index; the model was asked only 9
  times. Three misses: L30 ("Which papers address trust in QA answers, one by attributing ...") went to
  global; M26 ("Which two papers use counterfactuals, and for what ...") and M30 ("Which approach
  relies on a multilingual dense retriever, and which one folds ...") went to relate, because they ask
  for two named things and the rules read that as a relation. All three are questions about two
  papers, an in-between case.
- **Refusal:** 10 of 10 on the development set (the guards were tuned on it, so this proves little)
  and 9 of 10 on the fresh probes (F03 still gets an invented answer).
- **Cost per local answer $0.0031**, a tenth of the $0.03 target.
- **Easy set 29 of 30**, plain RAG 28 of 30: little room to differ.

## Relate: 14 of 20 explanations verified

The earlier re-check of the old texts predicted 17; the new run writes new texts and 14 pass. All 20
had a path of the right length (a consistency check: the expected paths came from the same graph).
The 6 warnings are sentences that name specific terms the explanation text does not have in its
context; nobody has read these explanations for faithfulness.

## Global search

Carried over from Phase 3 (the global code did not change): 100% on three criteria and 45% on
directness against plain RAG, with answers 3.4 times longer and a same-family judge. It was not run
again to save money; the page says so.

## What this means for the README and the demo

The honest summary is: **local search is a little better than plain RAG on questions that need two
or more passages (70% against 57% here, 53% in Phase 4), cites its sources reliably, refuses what it
cannot support, costs a third of a cent, but takes about five seconds and does not reach the 75%
target.** The README will say exactly that, with the table.
