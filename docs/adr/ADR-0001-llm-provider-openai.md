# ADR-0001: Use OpenAI as the LLM provider (Change Request CR-0001)

| Field | Value |
|---|---|
| Status | Proposed. Provider choice (OpenAI) made by owner on 2026-10-21; this ADR text awaits owner review; model IDs still to be verified |
| Blueprint | Advanced GraphLens Pipeline Blueprint v1.0 (2026-10-17) |
| Sections changed | Working assumptions, 2.2 Key Technical Decisions, 2.3 Technology Stack, 2.6 step 7, 2.7 external services, 5.3 Decisions Still Needed |
| Type | Change to a frozen decision (provider), no change to scope, security rules, schemas or API contracts |

## 1. Context

The blueprint assumes Anthropic Claude models for every LLM task:

| Task | Blueprint choice |
|---|---|
| Extraction (every chunk, cost-sensitive) | Claude Haiku, JSON output validated by Pydantic |
| Entity resolution, borderline pairs | LLM adjudication (model not named; extraction tier assumed) |
| Community reports | Claude Sonnet |
| Answers (local, global, relate, baseline) | Claude Sonnet |
| Router | Claude Haiku few-shot classifier with heuristic fallback |
| Evaluation judge | Claude Sonnet, answer order swapped, 10% human spot check |

The owner already pays for an OpenAI API key. A Claude Pro subscription does not include Anthropic API usage, so following the blueprint would need a new account and new billing.

The blueprint does not define a Change Request process. This ADR is the first one and also sets the simple process used from now on (section 6).

## 2. Decision

Use the **OpenAI API** for all LLM tasks, behind a small provider interface in our own code.

Model tiers replace model names:

| Task | Tier | Replaces |
|---|---|---|
| Extraction, resolution adjudication, router | `LLM_MODEL_SMALL` (low-cost OpenAI model) | Claude Haiku |
| Community reports, answers, judge | `LLM_MODEL_MAIN` (stronger OpenAI model) | Claude Sonnet |

Exact model IDs are **not** fixed in this ADR. They are chosen when the LLM is first used (Phase 1 baseline answers, Phase 2 extraction) after checking OpenAI's official model list, pricing and structured-output support on that day. The chosen IDs and date are recorded in an addendum to this ADR and on every index version (blueprint 2.11 already requires this).

## 3. What changes

- Stack 2.3: "Anthropic Python SDK" becomes "OpenAI Python SDK (pinned version)". Pydantic schemas and tenacity retries stay.
- Structured extraction uses OpenAI structured outputs (JSON schema). We **still** validate every response with Pydantic; the provider feature is not trusted alone.
- Environment variables: `OPENAI_API_KEY`, `LLM_MODEL_SMALL`, `LLM_MODEL_MAIN`. Only fake placeholders go in `.env.example`.
- Code shape: one module (for example `app/llm/`) with an `LLMClient` interface and an `OpenAIClient` implementation. A `FakeLLMClient` returns fixed, clearly labelled mock output for routine tests. No other code imports the OpenAI SDK directly.
- 5.3 "Extraction model: Haiku or Sonnet" becomes "small or main tier": try the small tier on a 5% sample, upgrade only if precision is below 0.80 (same rule as the blueprint).

## 4. What does NOT change

- Embeddings stay local: bge-base-en-v1.5, 768 dimensions. No OpenAI embeddings.
- All security rules in 2.8: document text is delimited and treated as data, no LLM-generated Cypher, secret redaction before logging or sending to the LLM, rate limits, daily cost cap.
- Cost targets in 1.2 (local at most $0.03, global at most $0.15 per query), token budgets in 2.6, the hard indexing cost cap, dry run and cost estimate.
- Schemas, API contracts and phase plan.

## 5. Consequences and risks

| Risk | Mitigation |
|---|---|
| Prompts in the blueprint were written with Claude in mind | Prompts are versioned; measure on the labeled set before full runs |
| Judge and answer model from the same provider may favour its own style | Keep answer-order swap and the 10% human spot check; record judge model on results |
| Cost per token differs from the blueprint's estimates | Re-run the cost estimator with OpenAI prices before any full indexing run; owner approves the estimate |
| OpenAI usage limits or alerts are not a guaranteed hard cap | Our own cost cap in code stops runs; owner also checks project budget settings in the OpenAI dashboard |
| Vendor lock-in | Single `LLMClient` interface; swapping back to Claude is a new ADR plus one adapter |

## 6. Change Request process (applies from now)

1. Write an ADR in `docs/adr/ADR-NNNN-short-name.md` with context, decision, what changes, what does not, and risks.
2. Owner approves in the project thread.
3. Mark the ADR "Accepted" and link it from the affected phase BRIEF.md.
4. Only then change code or docs that depend on it.

## 7. Open items

- Pick and verify `LLM_MODEL_SMALL` and `LLM_MODEL_MAIN` from official OpenAI docs at Phase 1/2 start.
- Commit this file to the repository once GitHub push access is connected.
