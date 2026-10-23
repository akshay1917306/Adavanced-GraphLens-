# Evaluation set v0: review page

Questions were drafted by Claude from the abstracts of the 25 papers. You are the judge.
For each question, check three things: (1) the question is clear, (2) the reference
answer is correct for what the quoted evidence says, (3) it is not too easy or odd.
Write your decision in the **Your decision** line (OK, CHANGE: ..., or DROP).

## Local questions (30)

### L01: How does the UDT-QA framework make tables and knowledge graphs usable for open-domain question answering?

- **Reference answer:** It turns tables from Wikipedia and graphs from Wikidata into text with a data-to-text verbalizer, so a retriever and reader can use them as extra knowledge sources.
- **Evidence** (2022.acl-long.113, `u_b8cfb9072b0d_0000`): "verbalized tables from Wikipedia and graphs from Wikidata are used as augmented knowledge sources"
- **Your decision:** 

### L02: What does the Retrieve-Generate-Filter technique create, and with how much human supervision?

- **Reference answer:** Counterfactual evaluation and training data for question answering, with minimal human supervision.
- **Evidence** (2022.acl-long.117, `u_6183c13e0bb6_0000`): "technique to create counterfactual evaluation and training data with minimal human supervision"
- **Your decision:** 

### L03: By how much does the sequence-to-sequence knowledge graph embedding model reduce model size compared with conventional embedding models?

- **Reference answer:** Up to 98%.
- **Evidence** (2022.acl-long.201, `u_381134ba1f9c_0000`): "reduces the model size up to 98% compared to conventional KGE models"
- **Your decision:** 

### L04: What are conditional answers in the ConditionalQA dataset?

- **Reference answer:** Answers that are only applicable when certain conditions apply.
- **Evidence** (2022.acl-long.253, `u_85db020b91cb_0000`): "the answers are only applicable when certain conditions apply"
- **Your decision:** 

### L05: What share of the Fusion-in-Decoder computation cost does KG-FiD need to reach comparable or better answer prediction?

- **Reference answer:** Less than 40% of the computation cost.
- **Evidence** (2022.acl-long.340, `u_732906872c61_0000`): "with less than 40% of the computation cost"
- **Your decision:** 

### L06: Which two datasets are used to evaluate the deep inductive logic reasoning model for multi-hop reading comprehension?

- **Reference answer:** WikiHop and MedHop.
- **Evidence** (2022.acl-long.343, `u_f1e807c70065_0000`): "we evaluate it on two reading comprehension datasets, namely WikiHop and MedHop"
- **Your decision:** 

### L07: How is user feedback simulated in the study of bandit learning for extractive question answering?

- **Reference answer:** By simulating feedback from supervised data, treating the problem as contextual bandit learning.
- **Evidence** (2022.acl-long.355, `u_e4de0d926563_0000`): "We study learning from user feedback for extractive question answering by simulating feedback using supervised data"
- **Your decision:** 

### L08: What F1 improvement does the ALCQA framework obtain on the CQA dataset?

- **Reference answer:** A 9.88% improvement in F1.
- **Evidence** (2022.emnlp-main.10, `u_a97dfd913ccf_0000`): "obtains a 9.88% improvements in the F1 metric on CQA dataset"
- **Your decision:** 

### L09: How much faster does SQUIRE converge than prior multi-hop knowledge graph reasoning methods?

- **Reference answer:** 4x to 7x faster.
- **Evidence** (2022.emnlp-main.107, `u_4724660473c3_0000`): "while converging 4x-7x faster"
- **Your decision:** 

### L10: How does the SF-TQA method generate query graphs for temporal question answering?

- **Reference answer:** By exploring relevant facts of the mentioned entities, with the exploration restricted by the Semantic Framework of Temporal Constraints.
- **Evidence** (2022.emnlp-main.122, `u_af4b5ba47ddd_0000`): "which generates query graphs by exploring the relevant facts of mentioned entities"
- **Your decision:** 

### L11: What dataset do the authors of the quantitative reasoning paper create?

- **Reference answer:** A unified dataset built on four previously released numerical question answering datasets over tabular data.
- **Evidence** (2022.emnlp-main.125, `u_039c611d6451_0000`): "we also create a unified dataset building on four previously released numerical QA datasets over tabular data"
- **Your decision:** 

### L12: What kind of data augmentation does the QADA framework use for question answering domain adaptation?

- **Reference answer:** Hidden space augmentation of the training samples.
- **Evidence** (2022.emnlp-main.147, `u_56d31becd18d_0000`): "we enrich the samples via hidden space augmentation"
- **Your decision:** 

### L13: By how much does the single end-to-end open-domain QA model beat the previous state of the art on Natural Questions and TriviaQA?

- **Reference answer:** By 1.0 and 0.7 exact match points.
- **Evidence** (2022.emnlp-main.198, `u_be1f94442adf_0000`): "our model outperforms the previous state-of-the-art model by 1.0 and 0.7 exact match scores"
- **Your decision:** 

### L14: How many areas of domain experts judged long-form answers in the evaluation study, and what did they provide?

- **Reference answer:** Experts in seven areas gave preference judgments over pairs of answers.
- **Evidence** (2023.acl-long.181, `u_e84a3c72733d_0000`): "We hire domain experts in seven areas to provide preference judgments over pairs of answers"
- **Your decision:** 

### L15: How does FAME organize its reasoning steps?

- **Reference answer:** As a structured entailment tree.
- **Evidence** (2023.acl-long.218, `u_bd66cdf3c6b3_0000`): "The reasoning steps are organized as a structured entailment tree"
- **Your decision:** 

### L16: What is the disconnected reasoning problem in multi-hop question answering?

- **Reference answer:** Models give the true answer using only one fact instead of reasoning over several facts.
- **Evidence** (2023.acl-long.231, `u_d37e80b0a561_0000`): "providing the true answer by only one fact, rather than multi-hop reasoning, which is referred to as disconnected reasoning problem"
- **Your decision:** 

### L17: How many human-written answers and supporting documents does the WikiHowQA benchmark contain?

- **Reference answer:** 11,746 human-written answers and 74,527 supporting documents.
- **Evidence** (2023.acl-long.290, `u_51284ef6b044_0000`): "The benchmark includes 11,746 human-written answers along with 74,527 supporting documents"
- **Your decision:** 

### L18: What share of lexical matching failures in open-domain QA evaluation is due to semantically equivalent answers?

- **Reference answer:** More than 50%.
- **Evidence** (2023.acl-long.307, `u_61676b02aa27_0000`): "more than 50% of lexical matching failures are attributed to semantically equivalent answers"
- **Your decision:** 

### L19: From how many existing QA datasets was the Open Long-Tailed QA dataset curated?

- **Reference answer:** 43 existing QA datasets.
- **Evidence** (2023.acl-long.351, `u_533dbf92ffe5_0000`): "a large-scale OLTQA dataset we curate from 43 existing QA datasets"
- **Your decision:** 

### L20: What share of answers in the cross-lingual attribution study cannot be attributed to any retrieved passage?

- **Reference answer:** A substantial portion, up to 47% of answers that exactly match a gold reference.
- **Evidence** (2023.emnlp-main.10, `u_60ab7f2e85b3_0000`): "a substantial portion of the answers is not attributable to any retrieved passages (up to 47% of answers exactly matching a gold reference)"
- **Your decision:** 

### L21: How does the Hop, Union, Generate approach model rationales for multi-hop question answering?

- **Reference answer:** It explicitly models rationales as sets, which lets it capture interactions between documents and sentences.
- **Evidence** (2023.emnlp-main.1001, `u_08db683fca63_0000`): "explicitly modeling rationales as sets"
- **Your decision:** 

### L22: Into which three stages does the decontextualization framework split the task?

- **Reference answer:** Question generation, question answering and rewriting.
- **Evidence** (2023.emnlp-main.193, `u_d352bfc2d1e1_0000`): "decomposes the task into three stages: question generation, question answering, and rewriting"
- **Your decision:** 

### L23: What effect does background information have on users' over-reliance on incorrect QA predictions?

- **Reference answer:** Providing the relevant background helps users catch model errors and reduces over-reliance on incorrect predictions.
- **Evidence** (2023.emnlp-main.201, `u_71f8f712a4f8_0000`): "Providing the relevant background, however, helps users better catch model errors, reducing over-reliance on incorrect predictions"
- **Your decision:** 

### L24: How many subgraphs with synthesized questions are used to adapt ReasoningLM?

- **Reference answer:** 20,000 subgraphs.
- **Evidence** (2023.emnlp-main.228, `u_4e80cf74d13c_0000`): "20,000 subgraphs with synthesized questions"
- **Your decision:** 

### L25: On how many multi-hop QA datasets does GEMFormer improve performance over the baseline?

- **Reference answer:** Three.
- **Evidence** (2023.emnlp-main.262, `u_2dae343019ba_0000`): "performance on three MHQA datasets compared to the baseline"
- **Your decision:** 

### L26: Which datasets are used to test the inductive logic reasoning model and the counterfactual multi-hop QA approach?

- **Reference answer:** The inductive logic reasoning model is tested on WikiHop and MedHop; the counterfactual multi-hop approach on HotpotQA.
- **Evidence** (2022.acl-long.343, `u_f1e807c70065_0000`): "namely WikiHop and MedHop"
- **Evidence** (2023.acl-long.231, `u_d37e80b0a561_0000`): "Extensive experiments have been conducted on the benchmark HotpotQA dataset"
- **Your decision:** 

### L27: Which knowledge graph approaches in the corpus use an encoder-decoder Transformer, and for what?

- **Reference answer:** One uses it as a scalable knowledge graph embedding model for link prediction and question answering; SQUIRE uses it to translate a query into a path for multi-hop reasoning.
- **Evidence** (2022.acl-long.201, `u_381134ba1f9c_0000`): "an off-the-shelf encoder-decoder Transformer model can serve as a scalable and versatile KGE model"
- **Evidence** (2022.emnlp-main.107, `u_4724660473c3_0000`): "which utilizes an encoder-decoder Transformer structure to translate the query to a path"
- **Your decision:** 

### L28: How do KG-FiD and ReasoningLM each use graph structure for question answering?

- **Reference answer:** KG-FiD uses a graph neural network over a knowledge graph to re-rank retrieved passages; ReasoningLM uses a subgraph-aware self-attention mechanism to imitate a graph neural network inside a language model.
- **Evidence** (2022.acl-long.340, `u_732906872c61_0000`): "a graph neural network (GNN) to re-rank the passages and select only a top few for further processing"
- **Evidence** (2023.emnlp-main.228, `u_4e80cf74d13c_0000`): "we propose a subgraph-aware self-attention mechanism to imitate the GNN for performing structured reasoning"
- **Your decision:** 

### L29: What do the studies of open-domain QA evaluation and long-form QA evaluation conclude about evaluation methods?

- **Reference answer:** For open-domain QA there appears to be no substitute for human evaluation; for long-form QA no existing automatic metric predicts human preference judgments.
- **Evidence** (2023.acl-long.307, `u_61676b02aa27_0000`): "At this time, there appears to be no substitute for human evaluation"
- **Evidence** (2023.acl-long.181, `u_e84a3c72733d_0000`): "finding that no existing metrics are predictive of human preference judgments"
- **Your decision:** 

### L30: Which papers address trust in QA answers, one by attributing answers to sources and one by studying how users verify them?

- **Reference answer:** The cross-lingual attribution paper studies attributing answers to retrieved sources; the background-information paper shows that relevant background helps users catch model errors.
- **Evidence** (2023.emnlp-main.10, `u_60ab7f2e85b3_0000`): "Our work is the first to study attribution for cross-lingual question answering"
- **Evidence** (2023.emnlp-main.201, `u_71f8f712a4f8_0000`): "Providing the relevant background, however, helps users better catch model errors"
- **Your decision:** 

## Global questions (10)

### G01: What are the main research directions in this corpus?

- **Reference answer:** Question answering over knowledge graphs; multi-hop reasoning; open-domain QA with retrieval; evaluating QA systems; trust and attribution of answers; new datasets and benchmarks.
- **Evidence** (2023.emnlp-main.228, `u_4e80cf74d13c_0000`): "Question Answering over Knowledge Graph (KGQA) aims to seek answer entities"
- **Evidence** (2023.acl-long.231, `u_d37e80b0a561_0000`): "Multi-hop QA requires reasoning over multiple supporting facts to answer the question"
- **Evidence** (2022.emnlp-main.198, `u_be1f94442adf_0000`): "Recent approaches to Open-domain Question Answering refer to an external knowledge base"
- **Evidence** (2023.acl-long.181, `u_e84a3c72733d_0000`): "its flexibility poses enormous challenges for evaluation"
- **Evidence** (2023.emnlp-main.10, `u_60ab7f2e85b3_0000`): "Our work is the first to study attribution for cross-lingual question answering"
- **Evidence** (2023.acl-long.290, `u_51284ef6b044_0000`): "a new multi-document NFQA benchmark built on WikiHow"
- **Your decision:** 

### G02: Which papers in the corpus work with knowledge graphs, and for which tasks?

- **Reference answer:** KG link prediction and KGQA (sequence-to-sequence KGE); multi-hop KG reasoning (SQUIRE); temporal KGQA (SF-TQA); complex KBQA (ALCQA); KGQA with a pre-trained language model (ReasoningLM); open-domain QA with a knowledge graph (KG-FiD).
- **Evidence** (2022.acl-long.201, `u_381134ba1f9c_0000`): "state-of-the-art results for KG link prediction and incomplete KG question answering"
- **Evidence** (2022.emnlp-main.107, `u_4724660473c3_0000`): "Multi-hop knowledge graph (KG) reasoning has been widely studied in recent years"
- **Evidence** (2022.emnlp-main.122, `u_af4b5ba47ddd_0000`): "Answering factual questions with temporal intent over knowledge graphs"
- **Evidence** (2022.emnlp-main.10, `u_a97dfd913ccf_0000`): "Complex knowledge base question answering can be achieved by converting questions into sequences of predefined actions"
- **Evidence** (2023.emnlp-main.228, `u_4e80cf74d13c_0000`): "directly support subgraph reasoning for KGQA, namely ReasoningLM"
- **Evidence** (2022.acl-long.340, `u_732906872c61_0000`): "Our new model uses a knowledge graph to establish the structural relationship among the retrieved passages"
- **Your decision:** 

### G03: How do the papers in the corpus approach multi-hop reasoning?

- **Reference answer:** Inductive logic rules (DILR); causal counterfactual inference against shortcuts (counterfactual multi-hop QA); rationales modeled as sets (Hop, Union, Generate); a global memory (GEMFormer); paths generated by a sequence-to-sequence model (SQUIRE); a dataset requiring compositional logical reasoning (ConditionalQA).
- **Evidence** (2022.acl-long.343, `u_f1e807c70065_0000`): "inducing feasible rules that entail the target relation"
- **Evidence** (2023.acl-long.231, `u_d37e80b0a561_0000`): "a counterfactual inference is proposed to disentangle the disconnected reasoning from the total causal effect"
- **Evidence** (2023.emnlp-main.1001, `u_08db683fca63_0000`): "explicitly modeling rationales as sets"
- **Evidence** (2023.emnlp-main.262, `u_2dae343019ba_0000`): "first collects relevant information over the entire document to the memory"
- **Evidence** (2022.emnlp-main.107, `u_4724660473c3_0000`): "translate the query to a path"
- **Evidence** (2022.acl-long.253, `u_85db020b91cb_0000`): "Answering the questions requires compositional logical reasoning across complex context"
- **Your decision:** 

### G04: What new datasets or benchmarks are introduced in the corpus?

- **Reference answer:** ConditionalQA; WikiHowQA; XOR-AttriQA; an Open Long-Tailed QA dataset from 43 datasets; a unified numerical QA dataset over tables; gold decontextualizations for scientific snippets.
- **Evidence** (2022.acl-long.253, `u_85db020b91cb_0000`): "We call this dataset ConditionalQA"
- **Evidence** (2023.acl-long.290, `u_51284ef6b044_0000`): "we present WIKI HOWQA"
- **Evidence** (2023.emnlp-main.10, `u_60ab7f2e85b3_0000`): "we introduce the XOR-AttriQA dataset"
- **Evidence** (2023.acl-long.351, `u_533dbf92ffe5_0000`): "a large-scale OLTQA dataset we curate from 43 existing QA datasets"
- **Evidence** (2022.emnlp-main.125, `u_039c611d6451_0000`): "we also create a unified dataset building on four previously released numerical QA datasets"
- **Evidence** (2023.emnlp-main.193, `u_d352bfc2d1e1_0000`): "we collect gold decontextualizations from experienced scientific article readers"
- **Your decision:** 

### G05: How is the evaluation of question answering systems discussed across the corpus?

- **Reference answer:** Long-form answers need multi-faceted human evaluation because automatic metrics do not predict preferences; lexical matching underestimates open-domain QA models; a new human evaluation framework is proposed for multi-document non-factoid QA; attribution is evaluated for cross-lingual QA.
- **Evidence** (2023.acl-long.181, `u_e84a3c72733d_0000`): "We encourage future work to move away from a single"
- **Evidence** (2023.acl-long.307, `u_61676b02aa27_0000`): "Lexical matching remains the de facto evaluation method for open-domain question answering"
- **Evidence** (2023.acl-long.290, `u_51284ef6b044_0000`): "propose a novel human evaluation framework that utilizes highlighted relevant supporting passages"
- **Evidence** (2023.emnlp-main.10, `u_60ab7f2e85b3_0000`): "to assess the attribution level of a state-of-theart cross-lingual question answering (QA) system"
- **Your decision:** 

### G06: Which papers address factuality, faithfulness or attribution problems of language model answers?

- **Reference answer:** FAME builds faithful reasoning steps as entailment trees; the cross-lingual attribution paper finds many answers not attributable to retrieved passages; WikiHowQA targets factual consistency with supporting documents; the open-domain evaluation paper notes models struggle to detect hallucinations.
- **Evidence** (2023.acl-long.218, `u_bd66cdf3c6b3_0000`): "revealing the intermediate reasoning steps that the models faithfully follow remains challenging"
- **Evidence** (2023.emnlp-main.10, `u_60ab7f2e85b3_0000`): "their raw generations often fall short in factuality"
- **Evidence** (2023.acl-long.290, `u_51284ef6b044_0000`): "evaluate answers’ grounding and factual consistency in relation to supporting documents"
- **Evidence** (2023.acl-long.307, `u_61676b02aa27_0000`): "The automated models struggle in detecting hallucinations in LLM answers"
- **Your decision:** 

### G07: Which approaches aim to make question answering systems smaller or cheaper to run?

- **Reference answer:** The sequence-to-sequence KGE model cuts model size by up to 98%; KG-FiD uses under 40% of the computation; the single-model open-domain QA approach uses model capacity more efficiently; ReasoningLM needs fewer updated parameters and less training data.
- **Evidence** (2022.acl-long.201, `u_381134ba1f9c_0000`): "reduces the model size up to 98% compared to conventional KGE models"
- **Evidence** (2022.acl-long.340, `u_732906872c61_0000`): "with less than 40% of the computation cost"
- **Evidence** (2022.emnlp-main.198, `u_be1f94442adf_0000`): "which is a more efficient use of model capacity"
- **Evidence** (2023.emnlp-main.228, `u_4e80cf74d13c_0000`): "even with fewer updated parameters and less training data"
- **Your decision:** 

### G08: How do the papers handle robustness and adapting QA models to new domains or unseen tasks?

- **Reference answer:** Counterfactual data augmentation improves robustness; QADA adapts to unseen target domains with hidden space augmentation; OLTQA targets seen and unseen QA tasks; bandit learning from user feedback lets systems adapt to new domains without annotation; the quantitative reasoning method improves robustness as reasoning steps grow.
- **Evidence** (2022.acl-long.117, `u_6183c13e0bb6_0000`): "improvements to robustness to local perturbations"
- **Evidence** (2022.emnlp-main.147, `u_56d31becd18d_0000`): "adapt QA models to an unseen target domain"
- **Evidence** (2023.acl-long.351, `u_533dbf92ffe5_0000`): "optimizing performance over seen and unseen QA tasks"
- **Evidence** (2022.acl-long.355, `u_e4de0d926563_0000`): "deploy systems in new domains without any annotation"
- **Evidence** (2022.emnlp-main.125, `u_039c611d6451_0000`): "renders the models more robust against overfitting as the number of reasoning steps grows"
- **Your decision:** 

### G09: How are human users or human judges involved in the studies in this corpus?

- **Reference answer:** Users give feedback to improve extractive QA (bandit study); users' reliance on QA predictions is studied with and without background information; domain experts judge long-form answers; open-domain QA answers are evaluated manually; scientific article readers write gold decontextualizations.
- **Evidence** (2022.acl-long.355, `u_e4de0d926563_0000`): "can dramatically improve given feedback from users"
- **Evidence** (2023.emnlp-main.201, `u_71f8f712a4f8_0000`): "we study how users interact with QA systems in the absence of sufficient information to assess their predictions"
- **Evidence** (2023.acl-long.181, `u_e84a3c72733d_0000`): "We hire domain experts in seven areas"
- **Evidence** (2023.acl-long.307, `u_61676b02aa27_0000`): "by manually evaluating their answers on a subset of NQ-OPEN"
- **Evidence** (2023.emnlp-main.193, `u_d352bfc2d1e1_0000`): "gold decontextualizations from experienced scientific article readers"
- **Your decision:** 

### G10: Which retrieval techniques appear in the corpus papers?

- **Reference answer:** Retriever-reader frameworks over data and text (UDT-QA); a retriever with a GNN re-ranker (KG-FiD); retriever and reranker as attention inside one model; Retrieve-Generate-Filter counterfactual generation; retrieve-then-rerank to select in-context examples (OLTQA); retrieval of similar question-answer pairs (ALCQA).
- **Evidence** (2022.acl-long.113, `u_b8cfb9072b0d_0000`): "The retriever-reader framework is popular for open-domain question answering"
- **Evidence** (2022.acl-long.340, `u_732906872c61_0000`): "built on top of a dense passage retriever and a generative reader"
- **Evidence** (2022.emnlp-main.198, `u_be1f94442adf_0000`): "casting the retriever and the reranker as internal passage-wise attention mechanisms"
- **Evidence** (2022.acl-long.117, `u_6183c13e0bb6_0000`): "Retrieve-Generate- Filter (RGF) technique"
- **Evidence** (2023.acl-long.351, `u_533dbf92ffe5_0000`): "A retrieve-then-rerank frame is further introduced to select in-context examples"
- **Evidence** (2022.emnlp-main.10, `u_a97dfd913ccf_0000`): "we retrieve top-k similar question-answer pairs at the inference stage"
- **Your decision:** 
