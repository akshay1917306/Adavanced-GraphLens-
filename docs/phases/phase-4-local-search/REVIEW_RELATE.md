# Relate pairs: review

> **Owner review, 2026-11-01 (partial):** the owner marked **R01 to R05 OK** after reading them. For **R06 to R20 the owner said they do not know these topics** and asked Claude to change anything that looks wrong and otherwise keep it. Claude did **not** change or drop any pair, because the Phase 7 numbers were measured on these 20 pairs. R06 to R14 look sensible from their names; R15 to R20 are flagged as weak or indirect links. **This is a Claude screening that the owner accepted, not an independent human check of R06 to R20.** The evaluation notes must not call the relate pairs fully human-reviewed.

Each pair has a path that exists in the graph (found by a plain breadth-first
search). The graph is not perfect (relation precision 0.81), so please check that the
pair and the path make sense for someone who wants to know how two things are
connected. Answer per ID: `OK`, `DROP` (not a useful pair) or `CHANGE: ...`.

| ID | Pair | Hops | Known path | Relations | Your decision |
|---|---|---|---|---|---|
| R01 | ILP and multi-hop reading comprehension | 1 | ILP → multi-hop reading comprehension | ADDRESSES | OK |
| R02 | OLTQA model and Open Long-Tailed QA (OLTQA) | 1 | OLTQA model → Open Long-Tailed QA (OLTQA) | ADDRESSES | OK |
| R03 | TF-IDF and ODQA | 1 | TF-IDF → ODQA | ADDRESSES | OK |
| R04 | multi-step quantitative reasoning and FinQANet+CompAQT | 1 | multi-step quantitative reasoning → FinQANet+CompAQT | ADDRESSES | OK |
| R05 | rule-enhanced learning and AnyBURL | 1 | rule-enhanced learning → AnyBURL | USES | OK |
| R06 | Back KD and QA model | 2 | Back KD → Long-Tailed Question Answering in an Open World → QA model | USES, USES | OK (Claude screened: the path reads sensibly; the owner accepted it without checking the topic) |
| R07 | Chain-of-Thought and EntailmentBankQA | 2 | Chain-of-Thought → Faithful Question Answering with Monte-Carlo Planning → EntailmentBankQA | USES, USES | OK (Claude screened: the path reads sensibly; the owner accepted it without checking the topic) |
| R08 | DPR-PAQ and TriviaQA | 2 | DPR-PAQ → You Only Need One Model for Open-domain Question Answering → TriviaQA | USES, USES | OK (Claude screened: the path reads sensibly; the owner accepted it without checking the topic) |
| R09 | EviGen and FiD-KD | 2 | EviGen → Evaluating Open-Domain Question Answering in the Era of Large Language Models → FiD-KD | USES, USES | OK (Claude screened: the path reads sensibly; the owner accepted it without checking the topic) |
| R10 | MQA-3H and PLM | 2 | MQA-3H → ReasoningLM: Enabling Structural Subgraph Reasoning in Pre-trained Language Models for Question Answering over Knowledge Graph → PLM | USES, PROPOSES | OK (Claude screened: the path reads sensibly; the owner accepted it without checking the topic) |
| R11 | RoBERTa-large and FinQANet | 2 | RoBERTa-large → Improving compositional generalization for multi-step quantitative reasoning in question answering → FinQANet | USES, USES | OK (Claude screened: the path reads sensibly; the owner accepted it without checking the topic) |
| R12 | Static MKD and T5-base | 2 | Static MKD → Long-Tailed Question Answering in an Open World → T5-base | USES, USES | OK (Claude screened: the path reads sensibly; the owner accepted it without checking the topic) |
| R13 | T5-large and LLMs | 2 | T5-large → Faithful Question Answering with Monte-Carlo Planning → LLMs | USES, USES | OK (Claude screened: the path reads sensibly; the owner accepted it without checking the topic) |
| R14 | causal inference and counterfactual examples | 2 | causal inference → disconnected reasoning → counterfactual examples | ADDRESSES, ADDRESSES | OK (Claude screened: the path reads sensibly; the owner accepted it without checking the topic) |
| R15 | sequence-based methods and quantitative reasoning | 2 | sequence-based methods → our proposed framework → quantitative reasoning | IMPROVES_ON, ADDRESSES | OK, flagged by Claude: the middle node is the generic name 'our proposed framework', so the link says little (owner accepted without checking the topic) |
| R16 | GPT-3 and SQuAD | 3 | GPT-3 → KG-FiD: Infusing Knowledge Graph in Fusion-in-Decoder for Open-Domain Question Answering → REALM → SQuAD | USES, USES, EVALUATED_ON | OK, flagged by Claude: GPT-3 and SQuAD are linked only through a chain of three papers/methods; a weak, indirect link (owner accepted without checking the topic) |
| R17 | InstructGPT (zero-shot) and gpt-4 | 3 | InstructGPT (zero-shot) → Evaluating Open-Domain Question Answering in the Era of Large Language Models → GPT4-eval → gpt-4 | USES, PROPOSES, USES | OK, flagged by Claude: the path goes through a 'GPT4-eval' node of one paper; indirect (owner accepted without checking the topic) |
| R18 | MetaQA and EXAQT | 3 | MetaQA → PullNet → TimeQuestions → EXAQT | EVALUATED_ON, EVALUATED_ON, EVALUATED_ON | OK, flagged by Claude: three hops through shared benchmarks (PullNet, TimeQuestions); loose (owner accepted without checking the topic) |
| R19 | NELL23K and ComplEx | 3 | NELL23K → TransE → WikiKG90Mv2 → ComplEx | EVALUATED_ON, EVALUATED_ON, EVALUATED_ON | OK, flagged by Claude: NELL23K and ComplEx are linked only because both appear with the same benchmarks; a loose link (owner accepted without checking the topic) |
| R20 | state verifier V and KGQA | 3 | state verifier V → Faithful Question Answering with Monte-Carlo Planning → ChatGPT → KGQA | PROPOSES, USES, ADDRESSES | OK, flagged by Claude: the path passes through the hub node ChatGPT; loose (owner accepted without checking the topic) |
