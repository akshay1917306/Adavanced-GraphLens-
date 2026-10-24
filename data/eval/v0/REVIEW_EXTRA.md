# Evaluation set v0: review page

Questions were drafted by Claude from the abstracts of the 25 papers. You are the judge.
For each question, check three things: (1) the question is clear, (2) the reference
answer is correct for what the quoted evidence says, (3) it is not too easy or odd.
Write your decision in the **Your decision** line (OK, CHANGE: ..., or DROP).

## Global questions (10)

### G11: Which papers aim to make question answering explainable, faithful or attributable, and how?

- **Reference answer:** Entailment trees built with Monte-Carlo planning (FAME); rationales learned without supervision (Hop, Union, Generate); evidential paths for knowledge graph reasoning (SQUIRE); interpretable logic rules (deep inductive logic reasoning); attributing answers to retrieved sources (cross-lingual attribution).
- **Evidence** (2023.acl-long.218, `u_bd66cdf3c6b3_0001`): "The reasoning steps are organized as a structured entailment tree"
- **Evidence** (2023.emnlp-main.1001, `u_08db683fca63_0001`): "not only predicts answers but also identifies rationales"
- **Evidence** (2022.emnlp-main.107, `u_4724660473c3_0001`): "provide interpretable predictions on missing links with evidential paths"
- **Evidence** (2022.acl-long.343, `u_f1e807c70065_0001`): "logic-based approaches provide interpretable rules to infer the target answer"
- **Evidence** (2023.emnlp-main.10, `u_60ab7f2e85b3_0001`): "attribute the answer to a retrieved source"
- **Your decision:** 

### G12: What role do data augmentation, counterfactuals or simulated data play in the corpus?

- **Reference answer:** Hidden space augmentation of training samples (QADA); counterfactual training and evaluation data created by retrieve-generate-filter; user feedback simulated from supervised data (bandit learning).
- **Evidence** (2022.emnlp-main.147, `u_56d31becd18d_0001`): "introduces a novel data augmentation pipeline used to augment training QA samples"
- **Evidence** (2022.acl-long.117, `u_6183c13e0bb6_0001`): "create counterfactual evaluation and training data with minimal human supervision"
- **Evidence** (2022.acl-long.355, `u_e4de0d926563_0001`): "simulating feedback using supervised data"
- **Your decision:** 

### G13: How do the papers deal with long documents or evidence spread over several documents?

- **Reference answer:** Long context documents with logically related information (ConditionalQA); a global memory over a long document (GEMFormer); questions that need reasoning across multiple documents (WikiHowQA).
- **Evidence** (2022.acl-long.253, `u_85db020b91cb_0001`): "long context documents with information that is related in logically complex ways"
- **Evidence** (2023.emnlp-main.262, `u_2dae343019ba_0001`): "This task includes processing a long document and reasoning over the multiple parts of it"
- **Evidence** (2023.acl-long.290, `u_51284ef6b044_0001`): "many questions require reasoning across multiple documents"
- **Your decision:** 

### G14: Which papers study long-form or non-factoid answers, and what problems do they point out?

- **Reference answer:** Experts judge long-form answers and no existing metric predicts their preferences (critical evaluation of LFQA); non-factoid answers are passage-level and hard to construct and evaluate (WikiHowQA); longer candidate answers make matching with gold answers harder (evaluating open-domain QA with LLMs).
- **Evidence** (2023.acl-long.181, `u_e84a3c72733d_0001`): "no existing metrics are predictive of human preference judgments"
- **Evidence** (2023.acl-long.290, `u_51284ef6b044_0001`): "requiring passage-level answers that are difficult to construct and evaluate"
- **Evidence** (2023.acl-long.307, `u_61676b02aa27_0001`): "candidate answers become longer"
- **Your decision:** 

### G15: Which papers build their method around a pre-trained language model or an encoder-decoder Transformer, and for what?

- **Reference answer:** An encoder-decoder Transformer translating a query into a path (SQUIRE) and acting as a knowledge graph embedding model (sequence-to-sequence KG completion and QA); a pre-trained language model that supports subgraph reasoning (ReasoningLM); retriever and reranker as attention inside one Transformer (You Only Need One Model); a pre-trained language model aligning questions and KG artifacts (ALCQA).
- **Evidence** (2022.emnlp-main.107, `u_4724660473c3_0001`): "utilizes an encoder-decoder Transformer structure to translate the query to a path"
- **Evidence** (2022.acl-long.201, `u_381134ba1f9c_0001`): "an off-the-shelf encoder-decoder Transformer model can serve as a scalable and versatile KGE model"
- **Evidence** (2023.emnlp-main.228, `u_4e80cf74d13c_0001`): "develop a more capable PLM that can directly support subgraph reasoning for KGQA"
- **Evidence** (2022.emnlp-main.198, `u_be1f94442adf_0001`): "within the transformer architecture"
- **Evidence** (2022.emnlp-main.10, `u_a97dfd913ccf_0001`): "utilize a pretrained language model to implicitly align the question and KG artifacts"
- **Your decision:** 

### G16: Which papers handle special kinds of questions, such as temporal, numeric or conditional ones?

- **Reference answer:** Temporal questions over knowledge graphs (SF-TQA); multi-step quantitative reasoning where numeric and verbal cues interact (compositional generalization); answers that only hold under certain conditions (ConditionalQA).
- **Evidence** (2022.emnlp-main.122, `u_af4b5ba47ddd_0001`): "Answering factual questions with temporal intent over knowledge graphs"
- **Evidence** (2022.emnlp-main.125, `u_039c611d6451_0001`): "Quantitative reasoning is an important aspect of question answering"
- **Evidence** (2022.acl-long.253, `u_85db020b91cb_0001`): "the answers are only applicable when certain conditions apply"
- **Your decision:** 

### G17: Which papers improve the retriever-reader pipeline of open-domain question answering, and how?

- **Reference answer:** A knowledge graph linking the retrieved passages (KG-FiD); merging retriever, reranker and reader into one model (You Only Need One Model); a verbalizer that turns structured data into text for the retriever and reader (unified knowledge interface).
- **Evidence** (2022.acl-long.340, `u_732906872c61_0001`): "uses a knowledge graph to establish the structural relationship among the retrieved passages"
- **Evidence** (2022.emnlp-main.198, `u_be1f94442adf_0001`): "a single question answering model trained end-to-end"
- **Evidence** (2022.acl-long.113, `u_b8cfb9072b0d_0001`): "retrieverreader framework"
- **Your decision:** 

### G18: Which papers rewrite or transform questions, text or data as a step in their method?

- **Reference answer:** Rewriting questions to align them with actions (ALCQA); rewriting snippets so that they can be read on their own (decontextualization); turning structured data into text (data-to-text verbalizer).
- **Evidence** (2022.emnlp-main.10, `u_a97dfd913ccf_0001`): "We train a question rewriting model to align the question and each action"
- **Evidence** (2023.emnlp-main.193, `u_d352bfc2d1e1_0001`): "rewrite snippets from scientific documents to be read on their own"
- **Evidence** (2022.acl-long.113, `u_b8cfb9072b0d_0001`): "use the data-to-text method as a means for encoding structured knowledge"
- **Your decision:** 

### G19: Which papers point out weaknesses of existing models, metrics or practices, and which weaknesses?

- **Reference answer:** Metrics do not predict expert preferences (LFQA evaluation); lexical matching fails when a plausible answer is not in the gold list (evaluating open-domain QA); models rely on shortcuts instead of multi-hop reasoning (counterfactual multihop QA); raw generations of generative models often fall short in factuality (attribution for cross-lingual QA).
- **Evidence** (2023.acl-long.181, `u_e84a3c72733d_0001`): "no existing metrics are predictive of human preference judgments"
- **Evidence** (2023.acl-long.307, `u_61676b02aa27_0001`): "lexical matching fails completely when a plausible candidate answer does not appear in the list of gold answers"
- **Evidence** (2023.acl-long.231, `u_d37e80b0a561_0001`): "the existing QA models always rely on shortcuts"
- **Evidence** (2023.emnlp-main.10, `u_60ab7f2e85b3_0001`): "their raw generations often fall short in factuality"
- **Your decision:** 

### G20: Which papers propose one unified or simplified model in place of a multi-stage pipeline?

- **Reference answer:** One model for retrieval, reranking and reading (You Only Need One Model); one encoder-decoder Transformer in place of a multi-stage KGE pipeline (sequence-to-sequence KG completion and QA); a single PLM instead of PLM plus GNN (ReasoningLM); one unified model for many tasks (long-tailed QA).
- **Evidence** (2022.emnlp-main.198, `u_be1f94442adf_0001`): "This allows us to use a single question answering model trained end-to-end"
- **Evidence** (2022.acl-long.201, `u_381134ba1f9c_0001`): "integrated into a multi stage pipeline"
- **Evidence** (2023.emnlp-main.228, `u_4e80cf74d13c_0001`): "we aim to simplify the above two-module approach"
- **Evidence** (2023.acl-long.351, `u_533dbf92ffe5_0001`): "building a unified QA model supporting various tasks is vital"
- **Your decision:** 
