# Judge review: do you agree with the verdicts?

Answer A is the **plain-RAG baseline**, answer B is **global search** (the judge saw them
in both orders and did not know which was which). For each question, read both
answers and the verdicts. Reply per question with `agree`, or the criterion you
disagree with and why,
for example `V03 agree, V04 diversity: baseline is better`.
The judge is the same model family as the answerer; your check is the independent one.

## V01: G03 How do the papers in the corpus approach multi-hop reasoning?

### Answer A (baseline)

The papers approach multi-hop reasoning through various methods including explainable multi-hop QA systems that identify rationales leading to answers, either within single or multiple documents, often relying on supervised settings with rationale and answer annotations or exploring approaches without rationale annotations due to their scarcity and cost [1]. Another approach formalizes a causal graph to disentangle disconnected reasoning from true multi-hop reasoning by modeling direct causal effects and applying counterfactual multi-hop QA to improve reasoning capabilities [2]. Some methods break down questions into smaller modules or use modular designs with retrievers and entailment modules to adaptively update facts and provide detailed explanations [3]. Deep learning methods include memory-based models with attention mechanisms, graph neural networks for entity connections, path-finding formulations, and neurosymbolic learning integrating deep learning with logic programming to handle uncertainty and reasoning [5][6]. Additionally, multi-hop reasoning models are evaluated using benchmarks and metrics like Mean Reciprocal Rank and Hits at N, with training involving techniques such as beam search and inverse edges to generate multi-hop paths [4].

### Answer B (global search)

The papers in the corpus approach multi-hop reasoning through a diverse set of methods spanning neural networks, logic reasoning, graph-based models, and knowledge graph techniques.

A prominent theme is the integration of deep learning with symbolic or logical reasoning. For example, Deep Inductive Logic Reasoning (DILR) frameworks combine attention mechanisms, neural logic operators, and clause instantiation to progressively select and refine candidate rules for multi-hop reading comprehension, outperforming traditional logic programming baselines [C4][C7]. This approach highlights the benefit of combining neural attention with explicit logic reasoning to filter relevant information across multiple hops.

Graph-based approaches are also widely used. Many methods build entity or knowledge graphs to represent connections between documents or facts, enabling information propagation and structured reasoning. Pre-trained language models (PLMs) combined with graph neural networks (GNNs) enhance reasoning over knowledge graph subgraphs by improving question understanding and reasoning capabilities [C14]. Similarly, ReasoningLM introduces a subgraph-aware self-attention mechanism and adaptation tuning to improve structured multi-hop reasoning over knowledge graphs, outperforming baseline KGQA methods [C15]. KG-FiD integrates knowledge graphs and GNNs within a Fusion-in-Decoder architecture to support multi-hop reasoning over structured knowledge [C35].

Walk-based reasoning methods use reinforcement learning to train agents to navigate knowledge graphs from head to tail entities, with symbolic rule-based models improving interpretability [C5]. SQUIRE employs a sequence-to-sequence Transformer framework with rule-enhanced learning to infer evidential paths in knowledge graphs, improving interpretability and convergence [C11]. Verbalization techniques convert knowledge graph queries into textual sequences, unifying QA and link prediction tasks to facilitate reasoning [C37].

In multi-hop reading comprehension, modeling dependencies between documents is crucial. The failure of the HUG-Ind model at bridge-based reasoning due to lack of document connection modeling underscores this need [C36]. Bridge-based reasoning specifically requires connections between previously selected documents to enable multi-hop inference [C36]. GEMFormer uses a two-stage approach with uncertainty-guided global memory augmentation and RoBERTa embeddings to improve reasoning over multiple document parts [C8].

Counterfactual multi-hop reasoning methods based on BERT reduce disconnected reasoning by disentangling shortcut impacts using causal inference and adversarial examples, enhancing reasoning across multiple paragraphs [C3]. Explainable multi-hop QA systems predict answers while identifying minimal rationale sentences, sometimes without relying on rationale annotations, using multi-task loss functions and specialized architectures [C2].

Finally, generative QA readers with encoder-decoder architectures outperform extraction-based readers in handling complex multi-hop reasoning [C35].

In summary, the corpus covers a variety of approaches to multi-hop reasoning, including memory-based neural networks, neural-symbolic logic integration, graph neural networks over knowledge graphs, reinforcement learning for graph navigation, and generative QA models. A key insight is the importance of modeling document or entity connections explicitly and combining deep learning with structured reasoning to improve multi-hop inference.

### Verdicts (after both orders)

| Criterion | Winner | Judge's reasons (order 1; order 2) |
|---|---|---|
| comprehensiveness | B (global) | Answer A provides a detailed and extensive overview of multiple approaches, techniques, and specific examples from the corpus, covering a wide range of methods and insights. ; Answer B provides a more detailed and extensive overview of various methods, including specific frameworks, models, and examples, covering a wider range of approaches to multi-hop reasoning. |
| diversity | B (global) | Answer A discusses a broader variety of methods including neural-symbolic integration, graph neural networks, reinforcement learning, verbalization, counterfactual reasoning, and generative models, offering richer perspectives. ; Answer B presents a richer variety of perspectives, including neural networks, logic reasoning, graph-based models, reinforcement learning, and generative QA, whereas Answer A is more limited in scope. |
| empowerment | B (global) | Answer A explains the rationale behind different approaches and highlights key insights, enabling readers to understand the strengths and challenges of various multi-hop reasoning methods. ; Answer B helps the reader understand the topic deeply by explaining different techniques, their benefits, and challenges, enabling informed judgments about multi-hop reasoning approaches. |
| directness | tie | Answer A directly and clearly addresses how the papers approach multi-hop reasoning with specific examples and explanations, whereas Answer B is more general and less focused. ; Both answers directly address how the papers approach multi-hop reasoning, though Answer B is more elaborate, both are clear and specific in their explanations. |

**Your decision:** 

## V02: G04 What new datasets or benchmarks are introduced in the corpus?

### Answer A (baseline)

The corpus introduces a new dataset and benchmark called WIKI HOWQA, sourced from the WikiHow website, which consists of passage-level answers to "how to" questions [2]. This dataset fills a critical gap in resources for multi-document non-factoid question answering (MD-NFQA) [2]. Unlike previous datasets such as ELI5, which rely on automated methods for curating reference content, WIKI HOWQA uses texts parsed from relevant HTML pages chosen by the author of the corresponding WikiHow article [1]. The benchmark also includes a novel human-evaluation framework that leverages highlighted relevant passages to improve the quality and factual accuracy of NFQA assessments [3].

### Answer B (global search)

Several new datasets and benchmarks are introduced across the corpus, targeting diverse challenges in question answering (QA), reasoning, and attribution detection.

In the financial and tabular data domain, community C39 presents multiple datasets—FinQA, TAT-QA, HiTab, and MULTIHIERTT—that focus on quantitative reasoning tasks, providing complex challenges for models dealing with numerical and structured data [C39].

For complex reading comprehension, the ConditionalQA dataset is introduced, featuring questions with conditional answers that require compositional logical reasoning, thus pushing the boundaries of understanding nuanced question structures [C10].

WikiHowQA is a large-scale benchmark derived from WikiHow articles, designed for multi-document non-factoid QA tasks. This dataset emphasizes answering questions that require synthesizing information from multiple documents rather than simple fact retrieval [C5].

In the realm of entailment and reasoning, the EntailmentBank dataset is mentioned twice: once as a training resource for a controller model employing Monte-Carlo planning for faithful QA [C37], and also as a test split benchmark for evaluating entailment tree generation methods [C23]. This highlights its dual role in both training and evaluation of reasoning models.

Cross-lingual and multilingual QA is addressed by the XOR-AttriQA dataset, which evaluates attribution in multilingual QA systems, thus supporting research in language transfer and attribution accuracy across languages [C7].

Temporal reasoning in knowledge graph question answering (KGQA) is targeted by two related datasets: TempQuestions [C19] and TimeQuestions [C27]. Both focus on temporal intents, providing benchmarks to evaluate how well models handle time-sensitive queries in KGQA settings.

The CuratedTREC dataset offers a benchmark with gold standard answers formatted as regular expressions, facilitating precise QA evaluation [C4].

For long-form QA, the ELI5 dataset provides questions and supporting documents sourced from Reddit, enabling research into generating detailed, explanatory answers [C28].

Finally, attribution detection tasks are supported by the TyDi QA dataset with around 100k examples [C9], and a large-scale NLI dataset with approximately one million examples for tuning and evaluating multilingual attribution detection methods [C8].

Together, these datasets and benchmarks cover a wide spectrum of QA challenges, including quantitative reasoning, logical and compositional reasoning, multi-document synthesis, multilingual attribution, temporal reasoning, and long-form answer generation. They provide valuable resources for advancing QA systems across different domains and languages.

### Verdicts (after both orders)

| Criterion | Winner | Judge's reasons (order 1; order 2) |
|---|---|---|
| comprehensiveness | B (global) | Answer A covers a wide range of datasets and benchmarks across multiple domains and tasks, while Answer B focuses only on the WikiHowQA dataset. ; Answer B lists multiple datasets and benchmarks across various domains and tasks, providing a broad and detailed overview, whereas Answer A focuses only on one dataset. |
| diversity | B (global) | Answer A presents diverse datasets addressing various QA challenges including financial, temporal, multilingual, and attribution tasks, whereas Answer B discusses only one dataset from a single perspective. ; Answer B covers a wide range of datasets addressing different QA challenges, including financial, logical, multilingual, temporal, and long-form QA, while Answer A discusses only the WikiHowQA dataset. |
| empowerment | B (global) | Answer A provides detailed descriptions and contexts for each dataset, enabling readers to understand their purposes and applications, unlike Answer B which offers limited insight. ; Answer B equips the reader with detailed knowledge about various datasets and their specific purposes, enabling informed understanding of the QA landscape, unlike Answer A which is limited to one dataset. |
| directness | tie | Answer A directly and specifically lists multiple new datasets and benchmarks introduced in the corpus, fully addressing the question, while Answer B only partially addresses it with one example. ; Both answers directly address the question by naming new datasets and benchmarks introduced in the corpus, though Answer B is more extensive. |

**Your decision:** 

## V03: G06 Which papers address factuality, faithfulness or attribution problems of language model answers?

### Answer A (baseline)

Papers 2023.emnlp-main.10 (passages 1, 2, 3, 5, 6) address attribution and factuality problems of language model answers. They find that state-of-the-art cross-lingual QA systems lack attribution and that raw generations often fall short in factuality, proposing attribution detection techniques using models like PaLM 2 to improve attribution levels [1][2][3][5][6]. Paper 2023.acl-long.218 (passage 4) addresses faithfulness by proposing FAME, a method to produce faithful reasoning steps in question answering, organizing reasoning as entailment trees to prove answer correctness [4]. Thus, both papers 2023.emnlp-main.10 and 2023.acl-long.218 focus on factuality, faithfulness, or attribution issues in language model answers.

### Answer B (global search)

Several papers explicitly address factuality, faithfulness, and attribution problems in language model answers, focusing on improving reasoning validity, answer support, and evaluation metrics.

Faithfulness and reasoning validity are central themes in multiple works. Community C5 introduces the Selection-Inference (SI) method and Faithful Question Answering (FQA) approach, which ensure that each reasoning step validly supports the final answer, thereby improving faithfulness and explainability in QA systems [C5]. Similarly, C8 proposes a controller model based on T5-large trained on EntailmentBank, using behavior cloning and a verifier to enhance reasoning trajectories and faithfulness through Monte-Carlo planning [C8]. Community C11 also formulates faithful question answering as a discrete decision-making problem using Monte-Carlo planning and organizes reasoning steps into structured entailment trees, demonstrating improvements across multiple datasets [C11].

Attribution problems—ensuring that answers are supported by appropriate evidence—are tackled by several papers. Community C1 introduces AIS, a novel evaluation metric for attribution in cross-lingual QA, and proposes XOR-AttriQA to improve attribution detection in closed-book QA systems [C1]. C2 discusses fine-tuning PaLM 2 on attribution data and leveraging Natural Language Inference (NLI) models to detect attribution and rerank passages, aiming to ensure QA predictions are supported by human-written text for safer deployment [C2]. Communities C3 and C10 focus on attribution detection using NLI fine-tuned models: C3 uses the TyDi QA dataset and shows strong performance in translate-test settings [C3], while C10 enhances multilingual attribution detection with fine-tuned mT5 models [C10].

Evaluation of factuality and faithfulness is another important aspect. Community C38 presents the WikiHowQA benchmark with evaluation methods and metrics to assess answer quality and factual consistency, directly relating to factuality and faithfulness [C38]. C34 discusses evaluation metrics like QAFactEval and datasets for long-form QA that comprehensively assess faithfulness and factuality of generated answers [C34]. Communities C9 and C35 emphasize evaluation methods for long-form QA, including human and expert judgments to assess factuality, completeness, and specificity, which are crucial for faithfulness in QA outputs [C9][C35].

Finally, C36 proposes the QADECONTEXT framework that improves faithfulness by modularizing snippet rewriting and decontextualization using question answering, employing soft interfaces between models to enhance output reliability [C36].

In summary, the addressed papers cover a range of approaches: improving reasoning faithfulness via structured entailment and planning (C5, C8, C11), enhancing attribution detection through NLI and fine-tuning (C1, C2, C3, C10), and developing evaluation benchmarks and metrics for factuality and faithfulness (C9, C34, C35, C38), as well as modular frameworks for faithful output generation (C36).

### Verdicts (after both orders)

| Criterion | Winner | Judge's reasons (order 1; order 2) |
|---|---|---|
| comprehensiveness | B (global) | Answer A covers a wide range of papers addressing factuality, faithfulness, and attribution, detailing methods, datasets, and evaluation metrics, whereas B mentions fewer papers with less detail. ; Answer B covers a wider range of papers and approaches addressing factuality, faithfulness, and attribution, including methods, evaluation metrics, and benchmarks, whereas A mentions fewer papers and details. |
| diversity | B (global) | Answer A provides multiple perspectives including reasoning validity, attribution detection, evaluation benchmarks, and modular frameworks, while B focuses mainly on two papers and their contributions. ; Answer B provides multiple perspectives including reasoning validity, attribution detection, evaluation metrics, and modular frameworks, while A focuses mainly on attribution detection and faithfulness methods. |
| empowerment | B (global) | Answer A explains various approaches and concepts in depth, enabling readers to understand different strategies and make informed judgments, unlike B which is more cursory. ; Answer B explains various methods and evaluation strategies, helping readers understand different approaches to address the problems, whereas A is more concise and less explanatory. |
| directness | tie | Answer A directly and specifically addresses the question by listing relevant papers and their contributions to factuality, faithfulness, and attribution, whereas B is less detailed and less explicit. ; Answer A directly names specific papers and their contributions to factuality, faithfulness, and attribution, providing a clear and focused response, while B is more elaborate and less concise. |

**Your decision:** 

## V04: G09 How are human users or human judges involved in the studies in this corpus?

### Answer A (baseline)

Human users participate in an online user-study where they answer questions by indicating agreement or disagreement with model predicted answers and their confidence level on a 5-point Likert scale; they also provide aggregate ratings on the utility of background information, confidence in the model, and self-confidence in their responses, along with optional free-text feedback and demographic information [1][4]. Human annotators are involved in judging the correctness of answers in open-domain QA by evaluating question/answer pairs without knowing the model source or gold status, using search engines to find supporting evidence, with disagreements resolved by a third annotator [6]. Non-expert crowdworkers are used to evaluate long-form answers, sometimes with access to evidence documents and optional justifications, though their reliability in judging correctness without domain expertise or full evidence access is questioned [3]. Human evaluators also assess model answers in comparison to human-written answers, as in the WebGPT dataset, where assessors prefer model answers 69% of the time, though supporting documents are not always released [5]. Simulation studies use simulated user feedback as a learning signal for QA systems, but actual human feedback is suggested as future work beyond simulation [2].

### Answer B (global search)

Human users and judges play a central role in the studies within this corpus, primarily through various forms of evaluation and feedback mechanisms designed to assess and improve question answering (QA) systems.

One common approach involves human evaluation frameworks where judges assess the quality of QA outputs. For example, multi-document non-factoid QA systems are evaluated by human judges who check answer correctness and attentiveness, ensuring reliable assessment beyond automatic metrics [C2][C18]. Similarly, long-form question answering (LFQA) systems are evaluated using human and expert judgments focusing on factuality, completeness, and conciseness of answers [C13][C9]. Human preference data also serves as a benchmark for evaluating the factuality and coherence of long-form answers, highlighting the importance of human judgment in quality assessment [C6].

A/B testing is another human-involved evaluation method where annotators compare pairs of answers to select the better one, providing comparative quality judgments that guide system improvements [C3]. Additionally, Wizard-of-Oz experiments and online user studies involve human users interacting with QA systems under controlled conditions to analyze user reliance and confidence, thus incorporating real user behavior into system evaluation [C1].

Human involvement extends to dataset creation and maintenance. The CuratedTREC dataset, a long-standing resource with gold standard answers, reflects human curation efforts that provide benchmarks for QA evaluation [C37]. This dataset’s longevity underscores the sustained human role in creating reliable evaluation standards.

Beyond evaluation, explicit human feedback is used as a direct learning signal to improve model performance. For instance, supervised attention and span-level alignments in semantic parsing benefit from human feedback [C4]. Contextual bandit learning methods leverage binary user feedback to enhance extractive QA systems, showing how human users contribute to model training through interactive feedback [C30]. Furthermore, human annotation is employed to estimate oracle outputs necessary for computing learner regret, involving judges in approximating ideal system performance [C12].

In summary, human users and judges are involved in this corpus through experimental studies, annotation and evaluation frameworks, dataset curation, and interactive feedback mechanisms. Their roles are crucial for assessing answer quality, guiding model improvements, and establishing reliable benchmarks across various QA tasks.

### Verdicts (after both orders)

| Criterion | Winner | Judge's reasons (order 1; order 2) |
|---|---|---|
| comprehensiveness | B (global) | Answer A covers a wide range of human involvement including evaluation, feedback, dataset curation, and experimental studies, while Answer B focuses mainly on evaluation and user studies with less breadth. ; Answer B covers a wider range of human involvement including evaluation, dataset curation, interactive feedback, and training signals, providing a more complete picture. |
| diversity | B (global) | Answer A provides multiple perspectives such as human evaluation frameworks, A/B testing, Wizard-of-Oz experiments, dataset curation, and interactive feedback, whereas Answer B mainly discusses user studies and annotator judgments. ; Answer B presents multiple perspectives such as evaluation methods, dataset creation, user studies, and learning approaches, showing greater variety. |
| empowerment | B (global) | Answer A explains how human involvement impacts model improvement, evaluation quality, and benchmark creation, helping readers understand the significance of human roles in the studies, unlike Answer B which is more descriptive without deeper insights. ; Answer B explains how human roles impact QA system assessment and improvement, helping readers understand the significance of human involvement. |
| directness | tie | Answer A directly and clearly addresses the question by detailing various ways humans are involved in the corpus studies, while Answer B is less focused and more fragmented in its response. ; Answer A directly and specifically describes how human users and judges participate in studies with concrete examples and methods. |

**Your decision:** 

## V05: G10 Which retrieval techniques appear in the corpus papers?

### Answer A (baseline)

The retrieval techniques mentioned in the corpus papers include sparse retrieval based on TF-IDF or BM25 and dense retrieval based on contextualized embeddings generated by pre-trained language models (PLMs) [1]. Additionally, cross-lingual retrieval of passages in multiple languages is noted as a recent advancement in Open-Retrieval Question Answering (ORQA) [5]. There is also mention of retrievers that retrieve documents from a large corpus, such as Wikipedia, to support answer generation [1][5]. Furthermore, some works propose improvements like better training strategies, reranking based on retrieved passages, and knowledge distillation from reader to retriever [1]. Finally, one paper discusses the limitation of retrieving facts from a fixed corpus and suggests the potential of retrieving up-to-date information using a modern search engine as a retriever [6].

### Answer B (global search)

The corpus papers present a diverse range of retrieval techniques applied primarily in open-domain and multi-hop question answering (QA) tasks, leveraging both traditional and neural methods.

A prominent theme is the use of dense retrieval models, which embed queries and documents into vector spaces for similarity search. Dense Passage Retriever (DPR) is frequently mentioned, serving as a baseline or core retriever in several works, including WikiHowQA and open-domain QA frameworks [C39][C2]. Similarly, MDPR, a multilingual dense passage retriever based on mBERT, is used in CORA for cross-lingual QA [C35]. Dense retrieval is often combined with reranking or reading components to improve answer accuracy [C2][C24].

Traditional lexical retrieval methods like TF-IDF and BM25 also appear, especially in open-domain QA settings, often integrated with dense retrievers to balance precision and recall [C2]. The YONO model exemplifies an end-to-end architecture that unifies retrieval, reranking, and reading layers, trained with multiple losses to optimize retrieval quality [C24].

Multi-hop QA retrieval techniques frequently exploit knowledge graphs and entity-centric approaches. For example, HotpotQA fullwiki employs several retrievers such as Path-Retriever, CogQA, Entitycentric, Golden Retriever, HopRetriever, and SMRS, which utilize knowledge graphs, entity queries, and iterative document selection to navigate multi-hop reasoning paths [C1]. CogQA, Entitycentric, and Golden Retriever explicitly use entities extracted from query keywords to retrieve subsequent documents in multi-hop QA [C1]. KG-FiD further integrates knowledge graphs with graph neural networks (GNNs) for graph-based reranking, enhancing retrieval in open-domain QA [C37].

Other retrieval enhancements include reranking strategies based on natural language inference (NLI) models, as in CORA, which reranks passages by assessing attribution levels to improve retrieval quality [C35]. Siamese network encoders fine-tuned with contrastive loss are also used for retrieval in Faithful Question Answering [C40].

For QA over tabular data, retrieval incorporates structure-aware representations and tabular encoding, combined with generators that produce executable programs for answer derivation [C25]. Additionally, some approaches leverage large language models (LLMs) like GPT-4 and davinci in retrieve-then-answer pipelines, where retrieval precedes LLM-based answer generation [C3].

Sequence-to-sequence models such as BART and T5 are integrated with dense retrieval in frameworks like RAG, enabling document-level retrieval and generation [C17]. The OLTQA model uses a two-stage knowledge distillation process in a retrieve-then-rerank framework to address long-tailed QA challenges [C34].

In summary, the corpus highlights a rich variety of retrieval techniques ranging from traditional lexical methods (TF-IDF, BM25) to dense neural retrievers (DPR, MDPR), entity- and knowledge graph-based retrieval, reranking with NLI and graph neural networks, and integration with large language models and sequence-to-sequence architectures. These methods are often combined in multi-stage pipelines to enhance retrieval effectiveness for complex QA tasks.

### Verdicts (after both orders)

| Criterion | Winner | Judge's reasons (order 1; order 2) |
|---|---|---|
| comprehensiveness | B (global) | Answer A provides a detailed and extensive overview of various retrieval techniques, including dense and sparse methods, multi-hop QA approaches, reranking strategies, and integration with LLMs, covering more aspects than Answer B. ; Answer B provides a detailed and extensive overview of various retrieval techniques, including specific models, methods, and their applications across different QA tasks, covering more aspects than Answer A. |
| diversity | B (global) | Answer A discusses a wider variety of retrieval techniques and perspectives, such as knowledge graph-based retrieval, multi-hop QA, cross-lingual retrieval, and sequence-to-sequence models, whereas Answer B is more limited in scope. ; Answer B presents a wide range of retrieval approaches from traditional lexical methods to dense neural retrievers, knowledge graph-based methods, reranking strategies, and integration with large language models, offering a richer variety of perspectives. |
| empowerment | B (global) | Answer A offers detailed explanations and examples that help the reader understand different retrieval methods and their applications, enabling more informed judgments compared to the brief summary in Answer B. ; Answer B equips the reader with a deeper understanding of the retrieval landscape by explaining different techniques, their combinations, and contexts, enabling more informed judgments about retrieval methods. |
| directness | tie | Answer A directly and specifically addresses the question by enumerating and explaining the retrieval techniques appearing in the corpus papers, while Answer B is more general and less specific. ; Answer A directly lists retrieval techniques mentioned in the corpus papers in a concise manner, whereas Answer B, though comprehensive, is more elaborate and less succinct in directly answering the question. |

**Your decision:** 

## V06: G12 What role do data augmentation, counterfactuals or simulated data play in the corpus?

### Answer A (baseline)

Data augmentation, particularly counterfactual data augmentation (CDA), is used to improve model robustness and out-of-domain generalization by exposing models to minimal pairs that reduce spurious correlations and encourage learning of causal features [1][5][6]. Counterfactual data augmentation methods generate synthetic examples paired with original data, which have shown better performance than non-counterfactual augmentation methods that produce unpaired synthetic examples [1]. CDA is especially effective in low-resource settings, where augmenting limited in-domain data with counterfactual examples can significantly improve performance, nearly matching models trained on twice as much original data [3]. The paper's method, RGF, generates fully-labeled counterfactual examples that can be directly used for augmentation, and targets a broad range of semantic phenomena to avoid overfitting [4][1]. Overall, counterfactual and simulated data serve as a tool to probe and enhance model generalization and robustness in question answering tasks [5][6].

### Answer B (global search)

Data augmentation, counterfactuals, and simulated data play significant and diverse roles in the corpus, primarily aimed at improving model robustness, reasoning, and generalization in question answering (QA) and natural language understanding tasks.

**Counterfactual Data Augmentation (CDA)** is a prominent approach where interventions on specific attributes generate counterfactual examples to probe and enhance model behavior. CDA improves robustness and local consistency across various datasets, including BioASQ [C1]. Similarly, the **RGF method** creates counterfactual question-context-answer triples to augment training data, boosting performance and robustness on reading comprehension and open-domain QA datasets like AmbigQA and SQuAD v1.0 [C2].

More advanced counterfactual generation techniques involve **retrieval-guided methods** that use QED-based decomposition and fine-tuned T5 models to produce label-changing counterfactual questions. These are quality-controlled through noise filtering and round-trip consistency checks, evaluated on datasets such as AQA and QUOREF [C3]. 

Counterfactual reasoning also leverages **causal inference and causal graphs** to generate counterfactual examples that reduce disconnected reasoning in multi-hop QA models. This approach modifies training data distributions and uses specialized metrics like DiRe to evaluate improvements [C4]. Extensions of this idea include counterfactual multi-hop reasoning methods based on BERT architectures (e.g., HGN, DFGN), which use adversarial examples and causal inference to disentangle shortcut reasoning, significantly enhancing multi-hop QA performance on datasets like HotpotQA [C5].

**Simulated data** plays a role in reasoning models through techniques like Monte-Carlo planning, which simulates exploration of next states and uses a state verifier to estimate state scores for better action evaluation. This simulated planning outperforms other algorithms such as beam search and greedy methods, indicating that simulated exploration improves reasoning performance [C40]. 

In terms of data augmentation beyond counterfactuals, frameworks like **QADA** introduce hidden space augmentation techniques (e.g., attentive context cutoff, Dirichlet neighborhood sampling) to enrich training data for domain adaptation in QA, helping models learn domain-invariant features and generalize better across domains [C13]. The **Gold Agen-Qgen method** selects samples based on longest edit distance for question generation, outperforming random selection and ensemble models in improving model consistency, serving as an effective augmentation technique [C12].

Other related approaches include leveraging **knowledge bases** to collect alternative plausible answers, enhancing QA evaluation through augmented data [C37], and using **bandit learning methods** with explicit or simulated user feedback to improve extractive QA models and facilitate domain adaptation across datasets like SQuAD and NewsQA [C24][C33].

Finally, retriever-generator architectures for QA over tabular data incorporate causal reasoning and graph-based methods to enhance quantitative reasoning, supporting data augmentation through structured data representations [C35].

In summary, the corpus demonstrates a rich variety of approaches where counterfactual data augmentation, simulated data, and related augmentation techniques are central to improving robustness, reasoning quality, domain adaptation, and evaluation in QA and natural language understanding tasks.

### Verdicts (after both orders)

| Criterion | Winner | Judge's reasons (order 1; order 2) |
|---|---|---|
| comprehensiveness | B (global) | Answer A covers a wide range of methods and applications of data augmentation, counterfactuals, and simulated data across multiple datasets and techniques, providing detailed examples and references. ; Answer B covers a wider range of methods and applications of data augmentation, counterfactuals, and simulated data, including specific techniques, datasets, and evaluation metrics, providing a more detailed and thorough overview. |
| diversity | B (global) | Answer A presents diverse perspectives including counterfactual data augmentation, causal inference, simulated planning, domain adaptation, knowledge base augmentation, and bandit learning, whereas Answer B focuses mainly on counterfactual data augmentation. ; Answer B presents multiple perspectives such as causal inference, retrieval-guided methods, simulated planning, domain adaptation, and knowledge base augmentation, offering a richer variety of insights. |
| empowerment | B (global) | Answer A explains various approaches and their impacts in detail, enabling readers to understand how these techniques improve robustness and reasoning, thus better equipping them to make informed judgments. ; Answer B equips the reader with detailed examples, methods, and contexts that help understand how these techniques improve QA models and how to evaluate them, enabling informed judgments. |
| directness | tie | Answer A directly and specifically addresses the role of data augmentation, counterfactuals, and simulated data in the corpus with clear examples and explanations, while Answer B is more general and less detailed. ; Answer A directly and succinctly addresses the role of data augmentation and counterfactuals in improving robustness and generalization, while Answer B, though comprehensive, is more elaborate and less concise. |

**Your decision:** 

## V07: G13 How do the papers deal with long documents or evidence spread over several documents?

### Answer A (baseline)

The papers address long documents and evidence spread over several documents by proposing specialized models and methods. One approach is GEMFormer, which augments pre-trained language models with a memory to store global information relevant to the task, processing long inputs concatenated with a memory sequence of important tokens defined by language model uncertainty [2]. Another approach involves joint document selection models that consider dependencies between documents, as selecting documents independently may result in insufficient information when reasoning steps depend on one another [4]. Additionally, some datasets and tasks require reading multiple sections or entire long documents, such as academic papers or books, to collect relevant information for answering questions, highlighting the challenge of reasoning through long and complex contents [5]. Documents are also processed to retain hierarchical structures and crucial content while simplifying formats to manage long documents effectively [6].

### Answer B (global search)

The papers address the challenge of handling long documents or evidence spread across multiple documents through a variety of retrieval, reasoning, and evaluation strategies.

A common approach is the retrieve-then-answer or retrieve-then-rerank framework, where relevant paragraphs or passages are first retrieved from large corpora or entire documents before generating answers. This effectively narrows down the context to pertinent snippets, making it easier to handle long documents or multiple documents [C1][C20][C30]. For example, the OLTQA model mines knowledge from large pre-trained language models using retrieval and reranking to manage long-tailed QA scenarios involving dispersed evidence [C20].

Multi-hop question answering (QA) methods explicitly focus on reasoning over multiple documents or document parts. The HUG method selects relevant documents and sentences in stages before answer generation, enabling multi-hop reasoning without requiring rationale supervision [C15]. Similarly, Path-Retriever uses knowledge graphs to iteratively select documents forming paragraph-level reasoning paths, facilitating multi-hop reasoning across documents [C4]. Other multi-hop reading comprehension approaches employ graph-based and neurosymbolic learning techniques to integrate information from multiple text pieces [C10].

To improve reasoning over long documents, GEMFormer introduces uncertainty-guided global memory that collects relevant information across entire documents and integrates it with local context, enhancing the model’s ability to synthesize dispersed evidence [C19]. The Selection-Inference (SI) method iteratively generates reasoning trees to ensure faithful reasoning steps, which helps structure reasoning over long or multi-document inputs [C39].

Some methods attempt to process entire documents directly. For instance, a full document setting uses GPT-4 to answer questions by inputting the entire source document, addressing long documents holistically [C1]. However, challenges remain, as shown by the HUG-Ind model, which does not model dependencies between documents and fails at bridge-based reasoning, highlighting difficulties in reasoning over evidence spread across documents [C2].

To support evaluation of such methods, datasets and frameworks have been developed specifically for multi-document non-factoid QA. WikiHowQA is a benchmark designed for multi-document QA tasks [C23], and a human evaluation framework tailored for multi-document non-factoid QA (MD-NFQA) has been proposed to assess system performance in this context [C38].

Finally, decontextualization and rewriting techniques have been explored to make text snippets understandable independently of their original context, which aids in handling evidence spread over multiple documents by improving snippet interpretability [C36].

In summary, the papers employ retrieval-based frameworks, multi-hop reasoning with graph or memory mechanisms, full-document processing, and specialized evaluation datasets to tackle the challenges posed by long documents and evidence dispersed across multiple documents. They also highlight ongoing challenges in modeling inter-document dependencies effectively.

### Verdicts (after both orders)

| Criterion | Winner | Judge's reasons (order 1; order 2) |
|---|---|---|
| comprehensiveness | B (global) | Answer A covers a wide range of methods including retrieval frameworks, multi-hop reasoning, memory mechanisms, full-document processing, evaluation datasets, and challenges, while Answer B mentions fewer approaches and details. ; Answer B covers a wider range of methods, models, datasets, and challenges related to handling long documents and multi-document evidence, providing more detailed examples and explanations. |
| diversity | B (global) | Answer A provides diverse perspectives such as retrieval, multi-hop reasoning, memory augmentation, evaluation frameworks, and decontextualization, whereas Answer B focuses mainly on memory augmentation and document selection. ; Answer B presents multiple perspectives including retrieval frameworks, multi-hop reasoning, memory mechanisms, evaluation datasets, and decontextualization techniques, offering a richer variety of approaches. |
| empowerment | B (global) | Answer A explains various techniques and their purposes in detail, helping readers understand how different methods tackle long documents and dispersed evidence, while Answer B is more general and less explanatory. ; Answer B helps the reader understand different strategies and their implications, enabling informed judgments about the strengths and limitations of various methods. |
| directness | B (global) | Answer A directly and clearly addresses how papers deal with long documents and evidence spread over multiple documents with specific examples and methods, whereas Answer B is less specific and more general. ; Answer B directly and clearly addresses how the papers deal with long documents and multi-document evidence with specific examples and explanations, whereas Answer A is more general and less explicit. |

**Your decision:** 

## V08: G15 Which papers build their method around a pre-trained language model or an encoder-decoder Transformer, and for what?

### Answer A (baseline)

Paper 2022.emnlp-main.198 proposes a single language model YONO that generalizes retrieval, reranking, and reading as internal attention functions, trained end-to-end with a pre-trained encoder-decoder architecture adapted for retrieval and answer generation tasks [1][5]. Paper 2022.emnlp-main.10 uses a pretrained language model like BERT to encode concatenated question and KG artifact inputs, leveraging the cross-attention mechanism to align questions and knowledge graph artifacts for logical form generation in knowledge base question answering [2][4]. Paper 2023.emnlp-main.262 proposes GEMFormer, which augments a pre-trained language model with a memory module to store global information for multi-hop question answering over long documents, addressing limitations of attention-based token representations [6].

### Answer B (global search)

Several papers build their methods around pre-trained language models (PLMs) or encoder-decoder Transformer architectures, primarily for question answering (QA) tasks, often integrating knowledge graphs or retrieval components.

The KG-FiD method explicitly integrates knowledge graphs into the Fusion-in-Decoder (FiD) framework, which is an encoder-decoder Transformer based on T5. KG-FiD employs a two-stage reranking process—graph-based reranking and graph attention networks—before encoding passages with the FiD encoder to generate answers, improving open-domain QA performance [C37]. The FiD reading module itself uses T5 components (embedding, encoder, decoder) to process concatenated question and passage inputs and generate answers [C25].

Similarly, the YONO model is a unified encoder-decoder language model architecture designed for open-domain QA. It integrates retrieval, reranking, and reading layers into an end-to-end trainable system, leveraging the encoder-decoder Transformer framework for QA [C1].

KGT5 uses a sequence-to-sequence encoder-decoder Transformer architecture based on T5-small for knowledge graph link prediction and question answering, evaluated on multiple benchmarks. This shows the use of pre-trained encoder-decoder models for both KG reasoning and QA [C23].

The OLTQA model applies a retrieve-then-rerank framework that mines knowledge from large pre-trained language models through a two-stage knowledge distillation process. It uses an encoder-decoder QA model to tackle long-tailed QA tasks, demonstrating the use of PLMs for specialized QA challenges [C22]. Similarly, a prompt-enhanced encoder-decoder QA model addresses long-tailed QA by leveraging knowledge prompts mined from large PLMs and dynamically combining meta prompts [C20].

In Faithful Question Answering, a controller model based on T5-large is trained on the EntailmentBank dataset for sequence generation, improving reasoning trajectories via behavior cloning and verifier fine-tuning. This highlights the use of a pre-trained encoder-decoder Transformer for reasoning and QA [C6].

More broadly, many KGQA methods use PLMs as text encoders for question understanding and integrate graph neural networks for reasoning over knowledge graphs [C3]. BART and T5 sequence-to-sequence models serve as foundational generators and readers across multiple QA formats, including multiple-choice, Boolean, and abstractive QA [C33].

Finally, in multi-modal QA, multi-modal pre-training models—adapted PLMs capable of handling inputs from different modalities—are used for QA tasks, extending the encoder-decoder Transformer paradigm beyond text-only inputs [C38].

In summary, a variety of methods build on pre-trained encoder-decoder Transformers like T5 and BART for QA, often integrating retrieval, reranking, knowledge graphs, or multi-modal inputs to enhance performance across open-domain, long-tailed, and multi-modal QA tasks [C1][C3][C6][C20][C22][C23][C25][C33][C37][C38].

### Verdicts (after both orders)

| Criterion | Winner | Judge's reasons (order 1; order 2) |
|---|---|---|
| comprehensiveness | B (global) | Answer A covers multiple papers and details their use of pre-trained language models and encoder-decoder Transformers across various QA tasks, while Answer B mentions fewer papers with less detail. ; Answer B covers a wider range of papers and details about their use of pre-trained language models and encoder-decoder Transformers across various QA tasks and methods. |
| diversity | B (global) | Answer A provides a wider range of perspectives including different QA tasks, integration with knowledge graphs, multi-modal inputs, and various model architectures, whereas Answer B focuses narrowly on a few examples. ; Answer B provides multiple perspectives including different QA tasks, integration with knowledge graphs, retrieval, reranking, and multi-modal inputs, whereas A focuses on fewer examples. |
| empowerment | B (global) | Answer A explains how the models are used and their purposes, helping readers understand the applications and benefits of pre-trained models in QA, unlike Answer B which is more terse and less explanatory. ; Answer B explains how different models leverage pre-trained Transformers for specific purposes, helping readers understand the applications and contexts better. |
| directness | tie | Answer A directly addresses the question by explicitly naming papers, models, and their purposes related to pre-trained language models and encoder-decoder Transformers, while Answer B is less direct and more fragmented. ; Answer A directly lists specific papers and their use of pre-trained models concisely, while B is more elaborate but less focused on directly answering the question. |

**Your decision:** 

## V09: G16 Which papers handle special kinds of questions, such as temporal, numeric or conditional ones?

### Answer A (baseline)

The paper from 2022.acl-long.253 introduces ConditionalQA, which handles conditional questions where answers depend on specific conditions and complex internal logic in documents, particularly in the public policy domain [4][6]. The paper from 2023.acl-long.307 discusses handling numeric answers with symbolic equivalence and temporal or spatial granularity discrepancies in questions and answers [1]. The paper from 2022.emnlp-main.122 focuses on temporal question answering over knowledge graphs, addressing temporal relations and temporal intents in questions [5].

### Answer B (global search)

Several papers specifically address special kinds of questions such as temporal, numeric, and conditional ones, often focusing on complex reasoning and knowledge graph question answering (KGQA).

For conditional questions, the C7 community introduces the ConditionalQA dataset designed for complex reading comprehension tasks where answers depend on compositional logical reasoning. They evaluate models like DocHopper and ETC on this dataset, highlighting approaches tailored to conditional answer generation [C7].

Temporal questions receive significant attention across multiple communities. The C1 community develops temporal question answering methods over knowledge graphs using Wikidata, incorporating logical restrictions and time-sensitive neural models to handle temporal queries effectively [C1]. Similarly, the C2 community uses TimeML annotations and interpretation structures (IS-1 and IS-2) to interpret temporal intents in KGQA, focusing on temporal constraints [C2]. The C10 community presents the TempQuestions dataset specifically for temporal intents in KGQA and proposes TEQUILA, a method that decomposes complex temporal relations using hand-crafted rules [C10]. The C16 community also targets temporal KGQA with the TimeQuestions benchmark and introduces EXAQT, a method that improves precision and Hit@1 metrics for temporal questions [C16].

Regarding numeric and quantitative reasoning, the C4 community proposes a framework addressing complex quantitative and logical question answering. Their approach covers quantitative counting, comparative reasoning, verification, and logical reasoning question types, thus handling numeric questions comprehensively [C4]. The C24 community discusses multi-step quantitative reasoning in QA, focusing on datasets like FinQA and TAT-QA. They introduce models such as CompAQT that improve compositional generalization for quantitative reasoning tasks [C24].

Additionally, the CuratedTREC dataset provides gold standard answers in the form of regular expressions, enabling evaluation of QA models on special question types including temporal, numeric, and conditional questions [C36]. The C39 community proposes a prompt-enhanced encoder-decoder QA model that addresses open long-tailed QA problems, which often include rare or special question types like temporal, numeric, or conditional questions, by leveraging knowledge and meta prompts [C39].

Finally, the C3 community employs BART and T5 models for diverse QA tasks including multiple-choice, Boolean, and abstractive QA, which can handle various question formats, potentially encompassing special question types [C3].

In summary, the literature covers a variety of special question types: conditional questions are addressed by ConditionalQA and related models [C7]; temporal questions are extensively studied with datasets and methods from C1, C2, C10, and C16 [C1][C2][C10][C16]; numeric and quantitative reasoning is tackled by C4 and C24 communities [C4][C24]; and broader approaches including prompt-based models and diverse QA architectures also contribute to handling these special questions [C36][C39][C3].

### Verdicts (after both orders)

| Criterion | Winner | Judge's reasons (order 1; order 2) |
|---|---|---|
| comprehensiveness | B (global) | Answer A covers multiple communities and datasets addressing conditional, temporal, and numeric questions in detail, while Answer B mentions only a few papers briefly. ; Answer B covers a wider range of papers and details about temporal, numeric, and conditional questions, including datasets, methods, and communities involved. |
| diversity | B (global) | Answer A provides a wide range of perspectives including different datasets, models, and question types, whereas Answer B is limited to a few specific papers. ; Answer B provides multiple perspectives including datasets, models, communities, and different QA approaches, whereas Answer A only briefly mentions three papers. |
| empowerment | B (global) | Answer A explains the approaches and datasets used for special question types, helping readers understand the scope and methods, unlike Answer B which is more cursory. ; Answer B helps the reader understand the topic by explaining various approaches, datasets, and models, enabling informed judgments about handling special question types. |
| directness | tie | Answer A directly and clearly addresses the question by categorizing papers by question type and summarizing their contributions, while Answer B is less explicit and detailed. ; Answer A directly and succinctly lists specific papers and their focus on special question types, while Answer B is more elaborate and less concise. |

**Your decision:** 

## V10: G19 Which papers point out weaknesses of existing models, metrics or practices, and which weaknesses?

### Answer A (baseline)

Paper 2022.acl-long.340 points out two weaknesses of the FiD model: (1) the independent assumption among passages is not justified because FiD cannot leverage semantic relationships among passages for embedding and answer generation, and (2) an efficiency bottleneck due to high computational cost when processing many retrieved passages [2]. Paper 2023.acl-long.290 discusses limitations including that not all documents are equally useful, the focus on highlighted relevant passages for human evaluation may miss some factual inconsistencies, and that evaluation of passage-level QA remains challenging due to difficulties in assessing factual correctness and consistency, especially when answers require complex reasoning [4]. Paper 2023.acl-long.290 also notes that standard automatic evaluation metrics like Rouge-X and BertScore poorly reflect actual model performance in NFQA [1]. Paper 2023.acl-long.181 highlights that existing automatic text generation metrics such as ROUGE were designed for other tasks and have not been validated for LFQA, with a major limitation being the huge space of valid output answers for any given question [5]. Additionally, it notes that metrics for faithfulness assume access to evidence documents and evaluates faithfulness by comparing answers to evidence, implying challenges in faithfulness evaluation [6]. Paper 2022.acl-long.201 points out that KGT5 sometimes falls behind baselines on small datasets due to Transformer models struggling when data is scarce, indicating a weakness in scalability and versatility [3].

### Answer B (global search)

Several papers highlight weaknesses in existing models, metrics, and practices across various QA tasks:

1. **Weaknesses in Models and Reasoning Approaches:**
   - The CQA dataset exposes challenges for graph-based methods in handling Quantitative and Comparative Reasoning questions, indicating these methods struggle with certain complex question types [C37].
   - Multi-hop QA models suffer from "disconnected reasoning," where models take shortcuts instead of performing genuine multi-step reasoning, revealing a fundamental weakness in current multi-hop QA practices [C15][C23].
   - The HUG-Ind model fails at bridge-based reasoning because it assumes document independence, which is a flawed assumption for tasks requiring modeling of document dependencies. This points to weaknesses in document selection and reasoning methods that do not capture inter-document relationships [C26].
   - Data-to-text generation models are prone to hallucination (generating incorrect or unsupported information), a known weakness addressed by customized loss functions to reduce such errors [C38].
   - Existing models may lack robustness to input variations, as multi-task learning has been shown to improve robustness, implying that single-task models are vulnerable to input changes [C38].
   - GPT-3 shows limitations in domain-specific knowledge, such as history, where human answers are preferred, highlighting weaknesses in large language models in certain specialized domains [C12].

2. **Weaknesses in Evaluation Metrics and Practices:**
   - Exact-Match and F1 metrics have notable failure cases in evaluating open-domain QA models, prompting the development of improved evaluation methods like InstructGPT-eval and GPT4-eval that better capture semantic equivalence and reduce evaluation errors [C3].
   - Purely automated evaluation approaches for multi-document non-factoid QA are insufficient, necessitating human evaluation frameworks and semantic similarity methods to ensure reliable assessment [C14].
   - Existing metrics for long-form QA, such as Length, Always Human, Random, and GPT2-PPL baselines, face challenges in accurately assessing factuality and coherence, indicating weaknesses in current evaluation metrics for long-form answers [C19][C24].
   - Multilingual QA evaluation faces challenges, as seen in the use of Google Translate API for attribution evaluation, revealing weaknesses in cross-lingual attribution assessment practices [C18].

In summary, these papers collectively identify weaknesses in reasoning capabilities of models (especially multi-hop and graph-based methods), robustness to input variation, domain-specific knowledge, and hallucination in generation. On the evaluation side, they point out limitations of traditional metrics like Exact-Match and F1, the need for human-in-the-loop evaluation, and difficulties in multilingual and long-form QA assessment [C3][C15][C23][C26][C37][C38][C12][C14][C19][C24][C18].

### Verdicts (after both orders)

| Criterion | Winner | Judge's reasons (order 1; order 2) |
|---|---|---|
| comprehensiveness | B (global) | Answer A covers a broader range of weaknesses across models, metrics, and practices with multiple examples and detailed explanations. ; Answer B covers a broader range of weaknesses across models, metrics, and practices with multiple examples and detailed explanations, while Answer A focuses on fewer papers and specific weaknesses. |
| diversity | B (global) | Answer A provides a wider variety of perspectives including different model types, reasoning challenges, evaluation metrics, and domain-specific issues. ; Answer B provides a wider variety of perspectives including different QA tasks, model types, reasoning challenges, and evaluation issues, whereas Answer A is more narrowly focused. |
| empowerment | B (global) | Answer A helps the reader understand specific weaknesses and their implications, enabling informed judgments about model and metric limitations. ; Answer B helps the reader understand the weaknesses in context and implications for evaluation and model design, enabling more informed judgments, while Answer A is more descriptive without broader insights. |
| directness | tie | Answer A directly addresses the question by explicitly listing weaknesses and linking them to specific papers and contexts. ; Answer A directly lists specific weaknesses from each paper with clear references, whereas Answer B is more general and synthesizes information, making A more directly responsive to the question. |

**Your decision:** 

