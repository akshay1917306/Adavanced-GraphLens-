# Unanswerable questions: review

> **Owner review, 2026-11-01:** U01 to U10 all marked **OK** (the papers-only design is kept: refusing is intended). Before U06 to U10 were marked, the 25 papers were searched (text search in the database, no model): RETRO, Mistral, MS MARCO, Gemini, SuperGLUE, nDCG and MRR@10 appear **nowhere**. Two near-misses that do not make the questions answerable: `claude-v1` is one of four models a paper *tests* (not the Claude 2 technical report), and `msmarco` appears once only inside a model URL (`contriever-msmarco`), not as a leaderboard. ("BEIR" matched only inside the name Ribeiro.)

The right answer to each question below is a refusal, because the 25 papers do not
contain the answer. Five are far outside the topic; five are close to it but about
things that are not in the papers. Answer per ID: `OK`, `DROP` or `CHANGE: ...` (for
example if you think a paper does answer it).

| ID | Question | Why it cannot be answered | Your decision |
|---|---|---|---|
| U01 | What is the capital of France? | out of domain | OK |
| U02 | How do I bake sourdough bread at home? | out of domain | OK |
| U03 | Which team won the 2018 FIFA World Cup? | out of domain | OK |
| U04 | What are the common side effects of ibuprofen? | out of domain | OK |
| U05 | How tall is Mount Everest? | out of domain | OK |
| U06 | What nDCG@10 does the RETRO model reach on the BEIR benchmark? | RETRO is not in the papers | OK |
| U07 | How many parameters does the Mistral 7B model have, and what context window does it support? | Mistral is not in the papers | OK |
| U08 | What MRR@10 did the top system reach on the MS MARCO passage ranking leaderboard? | MS MARCO is not in the papers | OK |
| U09 | What accuracy does Gemini Ultra reach on SuperGLUE? | Gemini and SuperGLUE are not in the papers | OK |
| U10 | What did the authors of the Claude 2 technical report conclude about long-context question answering? | Claude 2 is not in the papers | OK |
