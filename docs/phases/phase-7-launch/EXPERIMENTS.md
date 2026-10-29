# Phase 7 step 3: refusal, relate explanations and context size

Run on 2026-10-29 with the owner's yes (cap $0.50). Raw results are in `data/eval/phase7/results/`.
All model calls use `gpt-4.1-mini`; the judge is the same model, so correctness numbers are
indicative, not independent. **Step 3 spend: $0.2906** (Phase 7 total so far about $0.30 of $3.00).

## 1. Refusal on questions the papers cannot answer

Two sets: the 10 development questions U01 to U10 (Phase 4; the weaknesses U09 and U10 were seen on
this set, so **fixes tuned on it prove little**) and 10 **fresh probes** F01 to F10, written after the
rules were designed (`data/eval/phase7/fresh_unanswerable.json`; each checked with a plain text search
of the 751 text units; drafted by me, **not reviewed by the owner**).

| System | U01 to U10 | F01 to F10 |
|---|---|---|
| Phase 4 system (measured then) | 8 of 10 refused | not run |
| First attempt of this phase: a stricter model prompt only | 9 of 10 (U10 answered) | 4 of 10 by marker; 5 more were refusals in plain words |
| **Final code** (original prompt plus three guards below) | **10 of 10** | **9 of 10** (F03 answered) |

Why each part is there:
- **A plain-word name is not enough** (`accuracy`, `claude`): it must also be close to something in
  the graph (closest-entity score at least 0.79). Measured: all 60 answerable development questions
  scored at least 0.81, "accuracy of Gemini Ultra on SuperGLUE" scored 0.745. Stops U09 and four fresh
  probes before any model call.
- **A version number after a known name is a different thing** ("Claude 2" when the papers only know
  "claude"): the name is demoted, and if "Claude 2" is not in the gathered evidence the question is
  refused before the model is called. Stops U10 (this model hallucinated an answer about a "Claude 2
  report" from an unrelated paper).
- **A refusal in plain words is a refusal.** The model often says "The provided context does not
  contain ..." instead of the marker; the screen then showed a normal answer with a "Citations
  checked" badge. A first sentence that is a plain refusal (and has no "but", "however" or ";") now
  becomes a refusal with that sentence as the reason. It matched 5 of the 6 non-marker refusals and
  **0 of the 60 answerable answers** (30 at 8,000 and 30 at 12,000 tokens). Turns five fresh probes
  into refusals.

No answerable question is blocked: 0 of the 30 hard and 0 of the 30 easy development questions stop
before the model (free check). **Still failing: F03** ("what did the authors of the GPT 4 technical
report conclude about reasoning?") gets an invented answer: its names exist in the papers, only the
asked fact does not. The stricter prompt did not fix it either (it was tried and **reverted**: it
changed nothing for U10 and F03 and cost one correct answer on the hard set).

## 2. Why 9 of 20 relate explanations failed the citation check

Cause, from the saved texts: **all 9** were "a sentence names an entity that is not in the context";
**none** cited a label that does not exist (0 unknown labels). The check looked at every graph entity
name inside a sentence, including plain or very common words ("complex", "relation", "QA model") and
junk entities such as "part of". After ignoring names that are weak or made only of function words,
the same saved texts give **17 of 20 verified** (before: 11). The 3 left (R12, R14, R20) name specific
terms the model wrote that are not in the context ("adaptive mutual knowledge distillation",
"multi-hop question answering", "KGQA datasets"): the check is right to flag them. The texts were
re-checked, not regenerated, and nobody has read the explanations for faithfulness.

## 3. Context size and prompt on the hard set (30 questions)

| Variant | Correct | Citation check | Answer cost per question | Mean time |
|---|---|---|---|---|
| Phase 4 system (8,000 tokens, original prompt) | 21 of 30 (70%) | 3 warnings (Phase 4) | about $0.0035 | 5.2 s |
| 8,000 tokens, stricter prompt | 20 of 30 (66.7%, 49 to 81%) | 27 verified, 3 warnings | $0.0031 | 5.8 s |
| 12,000 tokens, stricter prompt | 22 of 30 (73.3%, 56 to 86%) | 20 verified, 10 warnings | $0.0043 | 6.7 s |

Against the Phase 4 answers question by question: 8,000 tokens with the new prompt 0 better and 1
worse; 12,000 tokens 2 better and 1 worse. **Decision: keep 8,000 tokens (D68).** The 12,000-token
difference is two questions on a set of 30 with overlapping intervals, it costs about 38% more per
answer, adds about a second, and gives three times as many citation warnings. **Neither variant
reaches the 75% target**; Phase 4 already showed that the gold passage is often not among the first
eleven the model sees, and a larger window helped little. The target stays missed and will be
reported as missed.

## Limits of these numbers

- 30 and 10 questions: one question moves the percentage by 3 to 10 points.
- Same-family judge; the hard set was drafted by Claude and its review pages are still waiting for the owner.
- The refusal guards were designed after looking at U09, U10 and the saved answers; only F01 to F10 were not.
- The prompt and context experiments reused the same 30 hard questions as Phase 4.
