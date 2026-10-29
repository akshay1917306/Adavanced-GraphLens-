# Interview page

## One-minute pitch

GraphLens is an end-to-end GraphRAG system: papers → knowledge graph (entities, relations, 193
communities) → a router that picks local, relate, global or plain-RAG answering → a web screen with
cited, checked answers. I built it phase by phase with written gates, measured it honestly, and
wrote down the three targets it missed.

## Numbers to know (all in [EVALUATION.md](EVALUATION.md))

- 25 papers → 751 passages → 1,545 entities, 2,694 relations, 193 communities.
- Local search 70% vs plain RAG 57% on 30 hard multi-hop questions (target 75% and +15 points: missed).
- Citation support 99.1%; router 97%; $0.0031 per answer; p95 10.3 s (target 8 s: missed).
- Model spend stayed small: extraction about $2.40 once, Phase 7 about $0.62 in total, cents per run.

## Questions you may get, and straight answers

- **Why a graph and not just vectors?** For questions that join facts from several passages the graph
  gave +13 points on the hard set; on easy questions it makes no difference (29/30 vs 28/30), and it
  is slower (5 s vs 2 s) and more complex. So it is worth it only for multi-hop questions.
- **Why did you miss the target?** Retrieval is not the limit (95% of gold passages are reached); the
  context budget is (about 57% fit). A larger window did not clearly help. Honest next steps: smarter
  passage selection, a reranker, streaming for speed.
- **How do you know the numbers are real?** One clean run with fresh system names so no old answer is
  reused; script-generated report; raw JSON saved. Limits: questions drafted by Claude, judge from the
  same model family, 30 questions per set (interval 52 to 83%).
- **How did you stop hallucinations?** Every claim must cite a passage that exists and a second model
  call checks support (99% on a sample); unknown model versions ("Claude 2") are refused before the
  model is called; a plain-words refusal counts as a refusal. One fresh probe (F03) still fails.
- **Security?** Deny by default, signed visitor cookie, per-visitor data, rate limits, daily cost cap,
  CSP with nonce, no model-written Cypher, secret scan in CI. Not externally reviewed; no HTTPS yet.
- **What would you do next?** Owner review of the labels, a larger corpus, HTTPS and monitoring,
  streaming answers, automatic backups, and upgrading the PDF library with a re-baseline.
- **What went wrong along the way?** A router rule treated "link prediction" as a relate question
  (found by the first live test, fixed with tests); a prompt change meant to be stricter gave no gain
  and was reverted; a PDF library upgrade would have cost $2.40 of re-extraction, so the risk was
  accepted instead (D59).
