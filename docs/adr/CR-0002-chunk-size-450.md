# CR-0002: Text unit size 450 tokens (was about 600)

Status: **Approved by the owner on 2026-10-23** (option B)
Changes: blueprint G2 and section 2.5 (Chunk: "about 600 tokens with 100 tokens of overlap").
Affects: Phase 1 and every later phase that uses text units.

## Why

Two frozen decisions disagree. Blueprint 2.5 says text units of about 600 tokens. Decision
D9 says embeddings come from `bge-base-en-v1.5`, whose maximum input is **512 tokens**.
Anything longer is cut, so the end of the text is not embedded.

Measured on 598 real text units (25 papers, 2026-10-23, bge WordPiece tokenizer):

- 216 of 598 units (36%) were over 512 tokens; the longest was 786.
- bge counts about 1.03 tokens for every gpt (`o200k_base`) token.

## Decision

- Target size: **450 tokens** (counted with `o200k_base`), overlap **75 tokens**.
- 450 gpt tokens is about 465 bge tokens, which leaves room for the two special tokens and for
  papers whose ratio is a little higher.
- Sentence-aware chunking and section boundaries stay as they are.
- `CHUNKER_VERSION` becomes `2`. It is recorded in `documents.metadata` for every document.

## Consequences

- More units: **726 instead of 598** for the 25 papers (measured after the change), average
  308 tokens, largest 450. A little more storage.
- Measured again with the bge tokenizer: **3 of 726 units (0.4%)** are still over 512 bge
  tokens (largest 626). They are formula-heavy text that WordPiece splits into many pieces.
  This is below the 1% revisit limit, so it is accepted. The embedding step will report how
  many units it had to cut.
- Embedding cost and time grow in the same proportion. Embeddings are local, so no money cost.
- Later phases: extraction (Phase 2) runs once per unit, so there are about 30% more units to
  process. Estimate again before any paid run.
- Existing rows made with chunker version 1 must be re-ingested. Done for the development
  corpus on 2026-10-23 (only the `qa_v0` rows were removed).

## Revisit

Measure again after the real 200 to 300 paper corpus is loaded. If more than 1% of units exceed
512 bge tokens, lower the target again.
