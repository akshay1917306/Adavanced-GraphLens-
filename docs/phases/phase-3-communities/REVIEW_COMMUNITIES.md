# Community review: coherence

For each community below, read the title, the summary and the member list, then give a
**coherence rating from 1 to 5**: 5 = the members clearly belong together and the
title and summary describe them well; 3 = partly; 1 = the members are unrelated or the
report does
not match them. Reply with the ratings, for example `K01 4, K02 5, K03 2`. Short comments
on low ratings help. (Proposed bar: an average of at least 3.5.)

## K01: Unified Frameworks and Graph-Enhanced Methods for Open-Domain QA

- Level 0, 217 entities, community `c_a99724bd1178`
- **Summary:** This community focuses on advanced methods and frameworks for open-domain question answering (ODQA) that integrate structured data, text, and knowledge graphs. Key approaches include the UDT-QA framework that verbalizes structured data into natural language, the YONO model unifying retrieval and reading in a single architecture, and KG-FiD which enhances Fusion-in-Decoder with knowledge graph-based reranking. These methods leverage datasets like Natural Questions and TriviaQA and employ multi-stage retrieval and reranking strategies to improve answer accuracy. The community also explores the use of generative readers and dense retrieval models to enhance performance.
- **Members (most connected first):** You Only Need One Model for Open-domain Question Answering (Paper); NQ (Dataset); Open Domain Question Answering with A Unified Knowledge Interface (Paper); KG-FiD: Infusing Knowledge Graph in Fusion-in-Decoder for Open-Domain Question Answering (Paper); TriviaQA (Dataset); ODQA (Task); FiD (Method); DPR (Method); KG-FiD (Method); UDT-QA (Method); REALM (Method); retrieval layer (Method)
- **Findings:**
  - UDT-QA provides a semi-parametric framework unifying data and text for ODQA.
  - YONO model unifies retrieval, reranking, and reading in a single trainable architecture.
  - KG-FiD enhances Fusion-in-Decoder by integrating knowledge graphs and graph neural networks.
  - Retriever-reader frameworks are foundational in ODQA, benefiting from verbalized knowledge and dense retrieval.
- **Your rating (1 to 5):** 

## K02: WikiHowQA: Benchmark for Multi-Document Non-Factoid QA

- Level 0, 34 entities, community `c_d8b1056274a9`
- **Summary:** This community centers around the WikiHowQA benchmark, a dataset designed for multi-document non-factoid question answering tasks. It includes a large collection of human-written answers and supporting documents derived from WikiHow articles. The community also involves various evaluation methods, baseline models, and metrics to assess answer quality and factual consistency. Authors affiliated with RMIT University and Ural Federal University contributed to the development and analysis of this benchmark. The dataset is compared and contextualized with other query-focused multi-document summarization datasets and evaluation frameworks.
- **Members (most connected first):** WikiHowQA: A Comprehensive Benchmark for Multi-Document Non-Factoid Question Answering (Paper); WikiHowQA (Dataset); RMIT University (Organization); BART-large (Method); Novel N-Gram Percentage metric (Method); DPR + BART (Method); DPR + text-davinci-003 (Method); Falk Scholer (Author); Mark Sanderson (Author); Sofya Filippova (Author); Valeriia Bolotova (Author); Vladislav Blinov (Author)
- **Findings:**
  - WikiHowQA is a large-scale benchmark dataset for multi-document non-factoid question answering.
  - The benchmark employs multiple baseline models including DPR combined with BART and GPT-3 variants.
  - An information-augmented human evaluation framework improves annotation reliability.
  - Novel N-Gram Percentage metric and other quality metrics characterize dataset difficulty and quality.
- **Your rating (1 to 5):** 

## K03: SQUIRE Framework and Multi-hop Reasoning in Knowledge Graphs

- Level 0, 52 entities, community `c_c2d4c536a299`
- **Summary:** This community focuses on the SQUIRE framework, a sequence-to-sequence model designed for multi-hop reasoning over knowledge graphs. SQUIRE leverages Transformer encoders to generate contextualized representations and employs iterative training inspired by the DAgger algorithm to improve path prediction. The framework emphasizes interpretability by inferring evidential paths and uses rule-enhanced learning to handle noisy samples. It is evaluated on benchmark datasets such as FB15K237 and NELL995, outperforming previous reinforcement learning methods. The community also discusses related multi-hop reasoning methods and embedding techniques for knowledge graph completion.
- **Members (most connected first):** SQUIRE: A Sequence-to-sequence Framework for Multi-hop Knowledge Graph Reasoning (Paper); SQUIRE (Method); multi-hop reasoning (Task); FB15K237 (Dataset); FB15K237-20% (Dataset); MultiHopKG (Method); NELL23K (Dataset); NELL995 (Dataset); AnyBURL (Method); DacKGR (Method); MINERVA (Method); TransE (Method)
- **Findings:**
  - SQUIRE uses iterative training to reduce the history gap in multi-hop reasoning.
  - Transformer encoders are central to SQUIRE's contextualized representation generation.
  - SQUIRE outperforms previous reinforcement learning methods in multi-hop reasoning tasks.
  - Rule-enhanced learning in SQUIRE improves interpretability and robustness to noisy data.
- **Your rating (1 to 5):** 

## K04: Cross-Lingual Attribution in Multilingual Question Answering Systems

- Level 0, 68 entities, community `c_842849982503`
- **Summary:** This community focuses on research and methods for evaluating and improving attribution in cross-lingual question answering (QA) systems. It includes datasets like XOR-TyDiQA and XOR-AttriQA, models such as PaLM 2, CORA, and MT5-QA, and evaluation metrics like AIS. The community explores attribution detection techniques using natural language inference models, fine-tuned multilingual transformers, and translation-based evaluation methods. These components collectively aim to ensure that QA predictions are supported by accurate and multilingual evidence.
- **Members (most connected first):** Evaluating and Modeling Attribution for Cross-Lingual Question Answering (Paper); PaLM 2 (Method); CORA (Method); MDPR (Method); Google DeepMind (Organization); XOR-AttriQA (Dataset); cross-lingual question answering (Task); MT5-QA (Method); NLI models (Method); Attribution detection models (Method); MGEN (Method); Natural Language Inference models (Method)
- **Findings:**
  - AIS is a novel metric for evaluating attribution in cross-lingual QA.
  - PaLM 2 is a large language model fine-tuned for attribution detection in cross-lingual QA.
  - CORA integrates multilingual retrieval and generation models for attributed QA.
  - Fine-tuned mT5 models improve multilingual attribution detection using NLI datasets.
- **Your rating (1 to 5):** 

## K05: QA Frameworks and Methods for Snippet Decontextualization

- Level 0, 50 entities, community `c_1a80080d9f84`
- **Summary:** This community focuses on question answering (QA) frameworks and methods designed to decontextualize scientific text snippets, making them understandable independently of their original context. Central to this is the QADECONTEXT framework, which decomposes the task into question generation, answering, and rewriting stages, leveraging large language models (LLMs) such as Claude, llama2, and GPT-4. Various approaches including end-to-end prompting, retrieve-then-answer, and rewriting modules are explored to improve snippet clarity and accuracy. The community also includes research on sequence-based semantic parsing models and tools addressing snippet decontextualization challenges.
- **Members (most connected first):** A Question Answering Framework for Decontextualizing User-facing Snippets from Scientific Documents (Paper); QADECONTEXT (Method); decontextualization (Task); davinci (Method); question generation (Method); sequence-to-sequence model (Method); Rewriting (Method); gpt-4 (Method); retrieve-thenanswer (Method); text-davinci-003 (Method); Allen Institute for AI (Organization); Arman Cohan (Author)
- **Findings:**
  - QADECONTEXT framework improves snippet decontextualization by decomposing the task.
  - Large language models are integral to various QA and decontextualization methods.
  - Decontextualization involves rewriting snippets to be context-independent while preserving meaning.
  - Sequence-based semantic parsing models enhance decontextualization and QA tasks.
- **Your rating (1 to 5):** 

## K06: RGF Method for Counterfactual Data Augmentation in QA

- Level 1, 22 entities, community `c_eef9f73192c1`
- **Summary:** This community centers on the RGF method, which generates counterfactual question-context-answer triples to augment training data for reading comprehension and open-domain question answering tasks. RGF leverages multiple models including sequence-to-sequence question generation, retrieve-and-read QA models, and REALM-Qgen to produce diverse and semantically meaningful counterfactual examples. The method is evaluated on various datasets such as AmbigQA, SQuAD v1.0, TREC, QUOREF-C, and challenge sets, demonstrating improvements in performance, local consistency, and robustness. Key tasks addressed include correctness, fluency, directionality, and local robustness of models under small input perturbations. Overall, RGF enhances model robustness and accuracy by enriching training data with carefully generated counterfactuals.
- **Members (most connected first):** RGF (Method); AmbigQA (Dataset); local consistency (Task); reading comprehension (Task); Open-domain (Task); QUOREF-C (Dataset); REALM-Qgen (Method); SQuAD v1.0 (Dataset); TREC (Dataset); challenge sets (Dataset); contrast evaluation sets (Bartolo et al., 2020; Gardner et al., 2020) (Dataset); correctness (Task)
- **Findings:**
  - RGF improves reading comprehension performance via counterfactual data augmentation.
  - RGF uses multiple methods including REALM-Qgen and sequence-to-sequence question generation.
  - RGF enhances local consistency and robustness of QA models.
  - RGF addresses semantic diversity including directionality and fluency in generated data.
- **Your rating (1 to 5):** 

## K07: QA-Based Framework for Decontextualizing Scientific Snippets

- Level 1, 23 entities, community `c_4c727ed5d467`
- **Summary:** This community centers on a question answering (QA) framework designed to decontextualize user-facing snippets from scientific documents. The framework, named QADECONTEXT, decomposes the decontextualization task into stages including question generation, question answering, and rewriting. It leverages various datasets such as QASPER and S2ORC, and employs both closed-source and open-source large language models like Claude, llama2, and tülu. The framework improves over end-to-end prompting strategies by using modular components and soft interfaces between models. Evaluation metrics like SARI are repurposed to assess the quality of decontextualized snippets.
- **Members (most connected first):** A Question Answering Framework for Decontextualizing User-facing Snippets from Scientific Documents (Paper); QADECONTEXT (Method); question generation (Method); SARI (Method); claude (Method); llama2-chat-70b (Method); tülu-30b (Method); Choi et al., 2021 (Paper); Dasigi et al.’s (2021) dataset (Dataset); End-to-end only (Method); Lauscher et al.’s (2022) dataset (Dataset); Luu et al., 2021 (Paper)
- **Findings:**
  - QADECONTEXT framework decomposes decontextualization into question generation, answering, and rewriting.
  - QADECONTEXT outperforms end-to-end prompting strategies in snippet rewriting.
  - The framework uses both closed-source and open-source large language models for various components.
  - Datasets like QASPER and S2ORC provide domain-specific data for training and evaluation.
- **Your rating (1 to 5):** 

## K08: Evaluation Methods for Long-Form Question Answering

- Level 1, 13 entities, community `c_1c3e8d8c9d6c`
- **Summary:** This community focuses on the task of long-form question answering (LFQA), which involves generating detailed answers to open-ended questions. It includes various evaluation methods such as string-matching metrics, human annotations, and expert judgments to assess answer quality. Key evaluation aspects include factuality, completeness, conciseness, ease of understanding, and specificity. Several GPT-3 models are used both for generating answers and for predicting preferences between candidate answers. The community also discusses specialized metrics designed for ambiguous factoid questions.
- **Members (most connected first):** long-form question answering (Task); A/B judgments (Method); GPT-3 text-curie-001 (Method); GPT-3 text-davinci-002 model (175B) (Method); completeness (Method); conciseness (Method); crowdsourced human annotations (Method); ease of understanding (Method); factuality (Method); free-form justifications (Method); specificity (Method); string-matching metrics (Method)
- **Findings:**
  - Long-form question answering requires generating detailed, comprehensive answers.
  - Multiple evaluation aspects assess the quality of LFQA answers.
  - Human and expert judgments are crucial for evaluating LFQA answers.
  - String-matching metrics like ROUGE are used but have limitations.
- **Your rating (1 to 5):** 

## K09: Authors Affiliated with Zhejiang University's Computer Science College

- Level 1, 4 entities, community `c_43c957109f3a`
- **Summary:** This community consists of three authors—Weiming Lu, Xiaoxia Cheng, and Yechun Tang—all affiliated with the College of Computer Science and Technology at Zhejiang University. The relationships highlight the institutional connection between the authors and their organization. This grouping reflects a collaborative research environment within the same academic institution.
- **Members (most connected first):** College of Computer Science and Technology, Zhejiang University (Organization); Weiming Lu (Author); Xiaoxia Cheng (Author); Yechun Tang (Author)
- **Findings:**
  - All three authors are affiliated with the same academic institution.
- **Your rating (1 to 5):** 

## K10: Temporal Question Answering Methods and Dataset

- Level 1, 6 entities, community `c_b7bce7d5d71d`
- **Summary:** This community centers around the TempQuestions dataset, a benchmark designed to evaluate temporal intents in knowledge graph question answering (KGQA). Several methods, including AQQU, QUINT, and TEQUILA, are evaluated on this dataset to assess their performance. TEQUILA is a method that decomposes complex temporal relations using hand-crafted rules and is combined with AQQU and QUINT to improve their results. The improved versions, AQQU+TEQUILA and QUINT+TEQUILA, demonstrate enhanced performance on the TempQuestions benchmark. Overall, the community highlights the interplay between dataset and methods focused on temporal KGQA.
- **Members (most connected first):** TempQuestions (Dataset); AQQU (Method); AQQU+TEQUILA (Method); QUINT (Method); QUINT+TEQUILA (Method); TEQUILA (Method)
- **Findings:**
  - TempQuestions is a benchmark dataset focusing on temporal intents in KGQA.
  - TEQUILA uses hand-crafted rules to decompose complex temporal relations in KGQA.
  - AQQU and QUINT are general KGQA methods evaluated on TempQuestions.
  - Incorporating TEQUILA improves AQQU and QUINT performance on TempQuestions.
- **Your rating (1 to 5):** 

## K11: Explainable Multi-Hop QA Systems and Approaches

- Level 1, 9 entities, community `c_5a5486d29c6b`
- **Summary:** This community focuses on explainable multi-hop question answering (QA) systems that not only predict answers but also identify rationales, which are minimal sets of sentences across documents leading to the answer. The papers explore various methods including supervised learning with multi-task loss functions and specialized network architectures, as well as approaches that do not rely on rationale annotations. The entities are closely related through their shared goal of improving explainability in multi-hop QA by different methodological innovations. The community highlights both architectural designs and training strategies to enhance rationale prediction and answer accuracy.
- **Members (most connected first):** Explainable multi-hop QA systems (Method); Atanasova et al., 2022 (Paper); DeYoung et al., 2020 (Paper); Fang et al., 2020 (Paper); Glockner et al., 2020 (Paper); Groeneveld et al., 2020 (Paper); Joshi et al., 2020 (Paper); Lewis et al., 2020b (Paper); Tu et al., 2019 (Paper)
- **Findings:**
  - Explainable multi-hop QA systems predict answers and identify minimal rationale sentences.
  - Some papers explore explainable multi-hop QA without rationale annotations.
  - Multi-task loss functions are applied for supervised explainable multi-hop QA.
  - Specialized network architectures are designed for supervised explainable multi-hop QA.
- **Your rating (1 to 5):** 

## K12: Semantic Framework for Temporal Question Answering over Knowledge Graphs

- Level 1, 17 entities, community `c_687558d31d0a`
- **Summary:** This community centers on the SF-TQA method, a temporal question answering system that generates query graphs constrained by the Semantic Framework of Temporal Constraints (SF-TCons). SF-TCons provides interpretation structures to model temporal intents such as before/after, simultaneous, and including relations between events. The method uses entity linking (ELQ), knowledge graphs, and SPARQL 3 to execute queries and is evaluated on two benchmarks, achieving state-of-the-art results. The community also includes various interpretation structures like SEQUENT, PARTOF, and SAME ENTITY to handle different temporal constraints.
- **Members (most connected first):** Semantic Framework based Query Generation for Temporal Question Answering over Knowledge Graphs (Paper); SF-TQA (Method); SF-TCons (Method); KB graphs (Dataset); KGQA tasks (Task); temporal intents (Task); Semantic Framework of Temporal Constraints (Method); ELQ (Method); IS-4 to 6 (Method); PARTOF (Method); SAME ENTITY (Method); SEQUENT (Method)
- **Findings:**
  - SF-TQA is a method for temporal question answering over knowledge graphs.
  - SF-TCons is a semantic framework modeling temporal constraints in KGQA.
  - Interpretation structures SEQUENT, PARTOF, and SAME ENTITY represent temporal relations.
  - SF-TQA uses entity linking (ELQ) and knowledge graphs for answering questions.
- **Your rating (1 to 5):** 

## K13: SQUIRE Framework for Multi-hop Knowledge Graph Reasoning

- Level 1, 17 entities, community `c_1dea2c229cb9`
- **Summary:** This community centers on the SQUIRE framework, a sequence-to-sequence model designed for multi-hop reasoning over knowledge graphs. It employs a Transformer encoder to generate contextualized representations from query and path tokens, addressing challenges like the history gap in autoregressive models. The framework introduces iterative training inspired by the DAgger algorithm to improve sequential prediction by aggregating new paths based on previous model outputs. Evaluation metrics such as Hits@1 and datasets like NELL9954 are used to assess performance, with methods like no-constraint generation and self-consistency enhancing path generation and decoding.
- **Members (most connected first):** SQUIRE: A Sequence-to-sequence Framework for Multi-hop Knowledge Graph Reasoning (Paper); iterative training (Method); Hits@1 (Method); Transformer encoder (Method); no-constraint generation (Method); Adam (Method); DAgger algorithm (Method); Feiyu Xiong (Author); Juanzi Li (Author); Lei Hou (Author); NELL9954 (Dataset); Xin Lv (Author)
- **Findings:**
  - Iterative training narrows the history gap in multi-hop reasoning.
  - Transformer encoder computes contextualized representations for queries and paths.
  - No-constraint generation allows flexible path sequence generation.
  - Self-consistency improves decoding of target entities.
- **Your rating (1 to 5):** 

## K14: Tsinghua University AI Researchers and Affiliations

- Level 1, 6 entities, community `c_fd609258e721`
- **Summary:** This community centers around three authors—Changshui Zhang, Hong Zhao, and Ruixin Hong—who collaborated on the paper 'Faithful Question Answering with Monte-Carlo Planning.' All three authors are affiliated with multiple organizations within Tsinghua University, including the Department of Automation and the Institute for Artificial Intelligence (THUAI), as well as the Beijing National Research Center for Information Science and Technology (BNRist). The community highlights the interconnectedness of these researchers and their institutional affiliations, emphasizing a collaborative research environment within Tsinghua University and its associated centers.
- **Members (most connected first):** Changshui Zhang (Author); Hong Zhao (Author); Ruixin Hong (Author); Beijing National Research Center for Information Science and Technology (BNRist) (Organization); Department of Automation, Tsinghua University (Organization); Institute for Artificial Intelligence, Tsinghua University (THUAI) (Organization)
- **Findings:**
  - Three authors collaborated on a paper about faithful question answering.
  - All authors are affiliated with Beijing National Research Center for Information Science and Technology.
  - Authors are also affiliated with Tsinghua University's Department of Automation.
  - Institute for Artificial Intelligence at Tsinghua University is a key affiliation.
- **Your rating (1 to 5):** 

## K15: Adaptive Mutual Knowledge Distillation for Long-Tailed QA

- Level 1, 29 entities, community `c_8175c2d8fb51`
- **Summary:** This community centers on a research paper proposing novel methods for long-tailed question answering (QA) in an open-world setting. It introduces two student models, R1 and R2, trained with a retrieve-then-rerank framework and refined through mutual and adaptive mutual knowledge distillation techniques. The models are evaluated on a variety of QA datasets, including domain-specific and adversarial sets, to demonstrate improvements over baseline retrievers and ablated variants. The adaptive mutual knowledge distillation method selectively transfers knowledge only from better-performing models, enhancing training efficiency and performance.
- **Members (most connected first):** Long-Tailed Question Answering in an Open World (Paper); R1 (Method); R2 (Method); retrieve-then-rerank framework (Method); mutual knowledge distillation (Method); Dval (Dataset); BM25 Retriever (Method); EPR Retriever (Method); adaptive mutual knowledge distillation (Method); Pm (Method); w/o Re-ranker (Method); AdamW (Method)
- **Findings:**
  - The paper proposes two student models, R1 and R2, for long-tailed QA.
  - Adaptive mutual knowledge distillation improves model training by selective knowledge transfer.
  - The retrieve-then-rerank framework jointly trained with QA models enhances performance.
  - R2 model gradually outperforms R1 during training and improves over baseline retrievers.
- **Your rating (1 to 5):** 

## K16: ReasoningLM: Subgraph Reasoning in Pre-trained Language Models

- Level 2, 23 entities, community `c_196f9d9a53fd`
- **Summary:** This community centers on the ReasoningLM paper, which proposes methods to enable pre-trained language models (PLMs) to perform structured reasoning over knowledge graph subgraphs. Key contributions include a subgraph-aware self-attention mechanism and an adaptation tuning strategy using synthesized subgraphs and questions. The paper leverages large language models like ChatGPT for automatic data construction and question synthesis, and evaluates performance on datasets such as MQA-1H and Wikidata2. The components collectively aim to improve answer entity reasoning over subgraphs by integrating graph structure into PLM reasoning.
- **Members (most connected first):** ReasoningLM: Enabling Structural Subgraph Reasoning in Pre-trained Language Models for Question Answering over Knowledge Graph (Paper); ChatGPT (Method); subgraph-aware self-attention mechanism (Method); adaptation tuning strategy (Method); LLM-based synthesis (Method); Brown et al., 2020 (Paper); Chen et al., 2023 (Paper); GraphtNet (Method); Ji-Rong Wen (Author); Jinhao Jiang (Author); KQA Pro (Dataset); Kun Zhou (Author)
- **Findings:**
  - ReasoningLM introduces a subgraph-aware self-attention mechanism for PLMs.
  - An adaptation tuning strategy is proposed to adapt PLM parameters for subgraph reasoning.
  - Large language models such as ChatGPT are used for automatic data construction and question synthesis.
  - The paper evaluates ReasoningLM on datasets like MQA-1H and Wikidata2.
- **Your rating (1 to 5):** 

## K17: Data-to-Text Generation and Structured Data in ODQA

- Level 2, 9 entities, community `c_22ed12297c04`
- **Summary:** This community focuses on the use of structured data, such as tables, triples, and knowledge graphs, in open-domain question answering (ODQA) and data-to-text generation. Key entities include datasets like tables, triples, Freebase knowledge graph, and Wikipedia text, which serve as inputs for generating natural language passages. The generator G is a method designed to verbalize structured data into coherent text, evaluated on various data forms. Studies by Oguz et al. (2020) and Li et al. (2020) explore hybrid frameworks combining text and structured data for improved ODQA performance.
- **Members (most connected first):** tables (Dataset); data-to-text generator G (Method); Oguz et al. (2020) (Paper); Wikipedia text (Dataset); generator G (Method); Freebase knowledge graph (Dataset); Li et al. (2020) (Paper); structured data input D (Dataset); triples (Dataset)
- **Findings:**
  - Generator G converts structured data into natural language passages.
  - Oguz et al. (2020) utilize multiple structured data sources for ODQA.
  - Li et al. (2020) propose a hybrid framework combining text and tables.
  - Tables serve as a primary structured data format in this community.
- **Your rating (1 to 5):** 

## K18: Knowledge Graph Embedding Models and Wikidata5M Dataset

- Level 2, 6 entities, community `c_4459b3fe4488`
- **Summary:** This community centers on knowledge graph embedding (KGE) methods evaluated on the large-scale Wikidata5M dataset, which contains millions of entities and relations. Traditional KGE models create unique embeddings per entity but face scalability challenges. Methods like DKRL and KEPLER address these issues by using compositional embeddings derived from textual descriptions, improving scalability. ComplEx serves as a baseline method for link prediction, while NBFNet is noted as the best performing model on smaller benchmark knowledge graphs. The relationships among these methods highlight ongoing efforts to balance scalability and performance in knowledge graph completion tasks.
- **Members (most connected first):** Wikidata5M (Dataset); DKRL (Method); ComplEx (Method); KEPLER (Method); Traditional KGE models (Method); NBFNet (Method)
- **Findings:**
  - Wikidata5M is a large benchmark knowledge graph dataset used for evaluating link prediction.
  - Traditional KGE models scale linearly with the number of entities and have limited versatility.
  - DKRL uses compositional embeddings combining word embeddings and CNN encoders to improve scalability.
  - KEPLER employs a Transformer-based encoder combining KGE training with masked language modeling to enhance scalability.
- **Your rating (1 to 5):** 

## K19: Large Language Models Evaluated on Multi-hop KGQA Datasets

- Level 2, 3 entities, community `c_3e6b14b7d749`
- **Summary:** This community focuses on the use of Large Language Models (LLMs) such as Davinci-003 and ChatGPT for Knowledge Graph Question Answering (KGQA) tasks. The LLMs are evaluated on two specific multi-hop datasets, MQA-2H and MQA-3H, which are based on the OMDb knowledge graph. These datasets serve as benchmarks to assess the performance of LLMs in handling complex, multi-hop queries. The relationships indicate that the LLMs' capabilities are directly tested using these datasets to measure their effectiveness in KGQA.
- **Members (most connected first):** LLMs (Method); MQA-2H (Dataset); MQA-3H (Dataset)
- **Findings:**
  - LLMs achieve state-of-the-art performance on KGQA tasks.
  - MQA-2H is a multi-hop dataset used for evaluating KGQA systems.
  - MQA-3H is another multi-hop dataset for KGQA evaluation.
  - LLMs are evaluated on both MQA-2H and MQA-3H datasets.
- **Your rating (1 to 5):** 

## K20: KGT5: Seq2Seq Transformer for Knowledge Graph Link Prediction and QA

- Level 2, 24 entities, community `c_4c40065a5ee6`
- **Summary:** This community centers on the KGT5 method, a sequence-to-sequence approach using an encoder-decoder Transformer architecture based on T5-small for knowledge graph (KG) link prediction and question answering (QA). KGT5 is trained and evaluated on various datasets including Freebase, ComplexWebQuestions, MetaQA, WN18RR, and YAGO3-10, demonstrating its applicability across different KGQA and link prediction tasks. The method contrasts with conventional knowledge graph embedding models by generating sequences rather than scoring entities individually, and it incorporates techniques like neighbourhood-based reranking and the AdaFactor optimizer. The community also references multiple large-scale and domain-specific KG datasets used for training and benchmarking KGT5's performance.
- **Members (most connected first):** Sequence-to-Sequence Knowledge Graph Completion and Question Answering (Paper); KGT5 (Method); T5-small (Method); Freebase (Dataset); AdaFactor (Method); ComplexWebQuestions (CWQ) (Dataset); DBpedia (Dataset); Freebase-based datasets ComplexWebQuestions (Dataset); HuggingFace library (Method); MetaQA 1-hop (Dataset); MetaQA 2-hop (Dataset); MetaQA 3-hop (Dataset)
- **Findings:**
  - KGT5 is a sequence-to-sequence model using an encoder-decoder Transformer for KG link prediction and QA.
  - KGT5 is evaluated on multiple benchmark datasets including Freebase, ComplexWebQuestions, MetaQA, WN18RR, and YAGO3-10.
  - KGT5 improves upon conventional knowledge graph embedding models by sampling sequences instead of scoring entities.
  - Training uses only natural language question and answer entity pairs without ground truth queries.
- **Your rating (1 to 5):** 

