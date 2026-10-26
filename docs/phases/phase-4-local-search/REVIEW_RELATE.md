# Relate pairs: review

Each pair has a path that exists in the graph (found by a plain breadth-first
search). The graph is not perfect (relation precision 0.81), so please check that the
pair and the path make sense for someone who wants to know how two things are
connected. Answer per ID: `OK`, `DROP` (not a useful pair) or `CHANGE: ...`.

| ID | Pair | Hops | Known path | Relations | Your decision |
|---|---|---|---|---|---|
| R01 | ILP and multi-hop reading comprehension | 1 | ILP → multi-hop reading comprehension | ADDRESSES | |
| R02 | OLTQA model and Open Long-Tailed QA (OLTQA) | 1 | OLTQA model → Open Long-Tailed QA (OLTQA) | ADDRESSES | |
| R03 | TF-IDF and ODQA | 1 | TF-IDF → ODQA | ADDRESSES | |
| R04 | multi-step quantitative reasoning and FinQANet+CompAQT | 1 | multi-step quantitative reasoning → FinQANet+CompAQT | ADDRESSES | |
| R05 | rule-enhanced learning and AnyBURL | 1 | rule-enhanced learning → AnyBURL | USES | |
| R06 | Back KD and QA model | 2 | Back KD → Long-Tailed Question Answering in an Open World → QA model | USES, USES | |
| R07 | Chain-of-Thought and EntailmentBankQA | 2 | Chain-of-Thought → Faithful Question Answering with Monte-Carlo Planning → EntailmentBankQA | USES, USES | |
| R08 | DPR-PAQ and TriviaQA | 2 | DPR-PAQ → You Only Need One Model for Open-domain Question Answering → TriviaQA | USES, USES | |
| R09 | EviGen and FiD-KD | 2 | EviGen → Evaluating Open-Domain Question Answering in the Era of Large Language Models → FiD-KD | USES, USES | |
| R10 | MQA-3H and PLM | 2 | MQA-3H → ReasoningLM: Enabling Structural Subgraph Reasoning in Pre-trained Language Models for Question Answering over Knowledge Graph → PLM | USES, PROPOSES | |
| R11 | RoBERTa-large and FinQANet | 2 | RoBERTa-large → Improving compositional generalization for multi-step quantitative reasoning in question answering → FinQANet | USES, USES | |
| R12 | Static MKD and T5-base | 2 | Static MKD → Long-Tailed Question Answering in an Open World → T5-base | USES, USES | |
| R13 | T5-large and LLMs | 2 | T5-large → Faithful Question Answering with Monte-Carlo Planning → LLMs | USES, USES | |
| R14 | causal inference and counterfactual examples | 2 | causal inference → disconnected reasoning → counterfactual examples | ADDRESSES, ADDRESSES | |
| R15 | sequence-based methods and quantitative reasoning | 2 | sequence-based methods → our proposed framework → quantitative reasoning | IMPROVES_ON, ADDRESSES | |
| R16 | GPT-3 and SQuAD | 3 | GPT-3 → KG-FiD: Infusing Knowledge Graph in Fusion-in-Decoder for Open-Domain Question Answering → REALM → SQuAD | USES, USES, EVALUATED_ON | |
| R17 | InstructGPT (zero-shot) and gpt-4 | 3 | InstructGPT (zero-shot) → Evaluating Open-Domain Question Answering in the Era of Large Language Models → GPT4-eval → gpt-4 | USES, PROPOSES, USES | |
| R18 | MetaQA and EXAQT | 3 | MetaQA → PullNet → TimeQuestions → EXAQT | EVALUATED_ON, EVALUATED_ON, EVALUATED_ON | |
| R19 | NELL23K and ComplEx | 3 | NELL23K → TransE → WikiKG90Mv2 → ComplEx | EVALUATED_ON, EVALUATED_ON, EVALUATED_ON | |
| R20 | state verifier V and KGQA | 3 | state verifier V → Faithful Question Answering with Monte-Carlo Planning → ChatGPT → KGQA | PROPOSES, USES, ADDRESSES | |
