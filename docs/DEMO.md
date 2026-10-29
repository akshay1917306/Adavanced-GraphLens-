# Three-minute demo script

Before you start: `docker compose up -d`, open http://localhost:3000. Replay mode is enough (no key,
no cost); live mode is only needed for step 5. Restore the data first if the databases are empty
([runbook](RUNBOOK.md)) so Neo4j Browser has something to show.

| Time | Say | Show |
|---|---|---|
| 0:00 | "GraphLens answers questions about 25 research papers by following a knowledge graph, and shows its evidence." | The Ask screen. |
| 0:20 | "Here is a real question that needs two facts from different parts of a paper." | Click the first example (KGT5 model size and the two graphs). |
| 0:40 | "Every claim has a chip like T1 or E2. T is a text passage, E is a graph relation." | Click a chip: the passage opens with its paper. Point at the green `verified` citation badge. |
| 1:10 | "This is the evidence graph: only the entities and links this answer used." | The graph panel. |
| 1:30 | "It also refuses when the papers do not say." | Click the refusal example. Read the message. "A wrong confident answer is worse than no answer." |
| 1:55 | "Your history and saved answers are private to your browser; one button deletes everything." | History, Saved, Settings (delete all). |
| 2:15 | "How good is it? I measured it, and three targets are missed." | Open [EVALUATION.md](EVALUATION.md) table: 70% vs 57% plain RAG (target 75% and +15), p95 10.3 s (target 8 s). |
| 2:40 | "Why: the right passages are found, but only about half fit in the context window. I tested a bigger window; it did not clearly help and cost 38% more." | The three-misses paragraph in the README. |
| 2:55 | "Everything runs on one laptop with Docker; a local answer costs a third of a cent; backups are tested." | Close. |

Optional live step (about 20 seconds, costs about $0.003): switch to live mode and ask any
question from the hard set (`data/eval/`); show the route (local), the graph and the badge.

Do not claim: that it is secure or production-ready, that the numbers generalise beyond 25 papers,
or that the global result is a fair test (same-family judge, answers 3.4 times longer).
