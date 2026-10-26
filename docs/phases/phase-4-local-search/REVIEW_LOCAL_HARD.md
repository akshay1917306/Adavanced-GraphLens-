# Evaluation set v0: review page

Questions were drafted by Claude from the abstracts of the 25 papers. You are the judge.
For each question, check three things: (1) the question is clear, (2) the reference
answer is correct for what the quoted evidence says, (3) it is not too easy or odd.
Write your decision in the **Your decision** line (OK, CHANGE: ..., or DROP).

## Local questions (30)

### M01: How much computation can KG-FiD save with its early reranking setting, and which model is its main baseline?

- **Reference answer:** About 60% of the computation cost (with L1 = L/4 and N2 = N1/5); the main baseline is FiD.
- **Evidence** (2022.acl-long.340, `u_732906872c61_0017`): "we can reduce about 60% of computation cost"
- **Evidence** (2022.acl-long.340, `u_732906872c61_0020`): "We mainly compare KG-FiD with the baseline model FiD"
- **Your decision:** 

### M02: Which generator does the unified-knowledge-interface approach use for data-to-text, and on which test set is it evaluated intrinsically?

- **Reference answer:** It fine-tunes the pretrained T5-Large model as the generator; the intrinsic evaluation uses the DART test set.
- **Evidence** (2022.acl-long.113, `u_b8cfb9072b0d_0011`): "we use the pretrained T5-Large (Raffel et al., 2020) model as our generator"
- **Evidence** (2022.acl-long.113, `u_b8cfb9072b0d_0016`): "intrinsic evaluation on the DART test set"
- **Your decision:** 

### M03: What size of model does KGT5 use in its main experiments, and which two large knowledge graphs does it use to test link prediction?

- **Reference answer:** A model with the architecture of T5-small (about 60M parameters) trained without the pretrained weights; link prediction is tested on Wikidata5M and WikiKG90Mv2.
- **Evidence** (2022.acl-long.201, `u_381134ba1f9c_0021`): "a model with the same architecture as T5-small"
- **Evidence** (2022.acl-long.201, `u_381134ba1f9c_0015`): "We evaluate the link prediction capability of KGT5 on Wikidata5M"
- **Your decision:** 

### M04: How does ConditionalQA score an answer that comes with conditions, and what makes its questions hard?

- **Reference answer:** The score of the predicted answer is multiplied by the F1 of the predicted conditions against the oracle conditions; answering requires compositional logical reasoning across complex context.
- **Evidence** (2022.acl-long.253, `u_85db020b91cb_0013`): "the scoring function will also take into account the accuracy of predicted conditions"
- **Evidence** (2022.acl-long.253, `u_85db020b91cb_0001`): "Answering the questions requires compositional logical reasoning across complex context"
- **Your decision:** 

### M05: What is the maximum length of the paths SQUIRE samples for training, and what kind of model does it use to turn a query into a path?

- **Reference answer:** The sampled paths have a maximum length of 3 (N = 3); SQUIRE uses an encoder-decoder Transformer.
- **Evidence** (2022.emnlp-main.107, `u_4724660473c3_0011`): "with maximum lengthN = 3"
- **Evidence** (2022.emnlp-main.107, `u_4724660473c3_0001`): "encoder-decoder Transformer structure to translate the query to a path"
- **Your decision:** 

### M06: How many steps does SF-TQA's query generation have, and how much higher is its H@1 on TempQuestions than QUINT's?

- **Reference answer:** Two steps (constraint evocation and constraint grounding); its H@1 is 41.2 against 27.0 for QUINT, 14.2 points higher.
- **Evidence** (2022.emnlp-main.122, `u_af4b5ba47ddd_0011`): "The query generation consists of two steps"
- **Evidence** (2022.emnlp-main.122, `u_af4b5ba47ddd_0020`): "SF-TQA 41.2 42.2 48.8 41.1"
- **Evidence** (2022.emnlp-main.122, `u_af4b5ba47ddd_0020`): "QUINT 27.0 30.3 51.2 28.8"
- **Your decision:** 

### M07: How does CompAQT add alignment to the training loss, and how many questions does the paper use to structure its results discussion?

- **Reference answer:** It adds an alignment term to the loss that pulls the attention weights towards prior alignments built from heuristics (in the absence of gold alignments); the results are organised around four questions.
- **Evidence** (2022.emnlp-main.125, `u_039c611d6451_0010`): "we add the below term to the loss"
- **Evidence** (2022.emnlp-main.125, `u_039c611d6451_0017`): "we investigate the effectiveness of CompAQT through four questions"
- **Your decision:** 

### M08: On which five datasets does QADA report results, and what happens to the HotpotQA exact match when contrastive adaptation is removed?

- **Reference answer:** HotpotQA, NaturalQ., NewsQA, SearchQA and TriviaQA; without contrastive adaptation the HotpotQA EM drops from 50.80 to 48.21.
- **Evidence** (2022.emnlp-main.147, `u_56d31becd18d_0022`): "Model HotpotQA NaturalQ. NewsQA SearchQA TriviaQA"
- **Evidence** (2022.emnlp-main.147, `u_56d31becd18d_0022`): "w/o contrastive adaptation 48.21/64.54"
- **Evidence** (2022.emnlp-main.147, `u_56d31becd18d_0001`): "a novel selfsupervised framework called QADA for QA domain adaptation"
- **Your decision:** 

### M09: By how much does the single-model open-domain QA approach beat the previous best, and on which two datasets is it evaluated?

- **Reference answer:** It outperforms the previous state of the art by 1.0 and 0.7 exact match points; it is evaluated on Natural Questions and TriviaQA.
- **Evidence** (2022.emnlp-main.198, `u_be1f94442adf_0001`): "our model outperforms the previous state-of-the-art model by 1.0 and 0.7 exact match scores"
- **Evidence** (2022.emnlp-main.198, `u_be1f94442adf_0018`): "Natural Questions (Kwiatkowski et al., 2019) and TriviaQA (Joshi et al., 2017)"
- **Your decision:** 

### M10: What do the authors of the long-form QA evaluation study conclude about automatic metrics, and how do they study what makes one answer better than another?

- **Reference answer:** No existing metric is predictive of human preference judgments; they analyse the free-form justifications collected from expert annotators (and WebGPT crowd annotators).
- **Evidence** (2023.acl-long.181, `u_e84a3c72733d_0001`): "no existing metrics are predictive of human preference judgments"
- **Evidence** (2023.acl-long.181, `u_e84a3c72733d_0011`): "we perform an analysis on the free-form justifications"
- **Your decision:** 

### M11: Which dataset is FAME evaluated on, how many entailment trees does it contain, and what structure does FAME build for its reasoning?

- **Reference answer:** EntailmentBank, with 1,840 expert-annotated entailment trees (converted to EntailmentBankQA); FAME organises its reasoning steps as a structured entailment tree.
- **Evidence** (2023.acl-long.218, `u_bd66cdf3c6b3_0019`): "1,840 expert-annotated entailment trees"
- **Evidence** (2023.acl-long.218, `u_bd66cdf3c6b3_0001`): "The reasoning steps are organized as a structured entailment tree"
- **Your decision:** 

### M12: Which multi-hop architectures does the counterfactual multi-hop method get applied to besides BERT, and what problem does it set out to reduce?

- **Reference answer:** DFGN, HGN and XLNet in Dire; it targets the disconnected reasoning problem.
- **Evidence** (2023.acl-long.231, `u_d37e80b0a561_0022`): "DFGN (Qiu et al., 2019), HGN (Fang et al., 2019)"
- **Evidence** (2023.acl-long.231, `u_d37e80b0a561_0001`): "reduce the disconnected reasoning"
- **Your decision:** 

### M13: Which architecture is the WikiHowQA baseline built on, and how often did the first human-evaluation set-up prefer model answers over reference answers?

- **Reference answer:** Retrieval-Augmented Generation (RAG); in the conventional human evaluation simpler model-generated answers were preferred over reference answers 48% of the time.
- **Evidence** (2023.acl-long.290, `u_51284ef6b044_0018`): "we use the Retrieval-Augmented Generation (RAG)"
- **Evidence** (2023.acl-long.290, `u_51284ef6b044_0021`): "simpler modelgenerated answers were frequently (48% of the time) preferred over reference answers"
- **Your decision:** 

### M14: How many open-domain QA models and how many NQ-Open questions are used in the study of evaluation of open-domain QA with LLMs?

- **Reference answer:** 12 open-domain QA models; 301 questions randomly sampled from NQ-Open (1,490 unique question/answer pairs).
- **Evidence** (2023.acl-long.307, `u_61676b02aa27_0010`): "assess 12 open-domain QA models"
- **Evidence** (2023.acl-long.307, `u_61676b02aa27_0009`): "We randomly sample 301 questions from NQ"
- **Your decision:** 

### M15: How is the 'w/o head' training set of the long-tailed QA paper built, and between which kinds of tasks does the OLTQA model share knowledge?

- **Reference answer:** It is built by discarding the samples of head tasks, leaving samples from 16 tail tasks; the model shares knowledge between head, tail and unseen tasks.
- **Evidence** (2023.acl-long.351, `u_533dbf92ffe5_0025`): "discarding samples from head tasks"
- **Evidence** (2023.acl-long.351, `u_533dbf92ffe5_0001`): "knowledge sharing between head, tail and unseen tasks"
- **Your decision:** 

### M16: How many parameters does the ReasoningLM comparison list for EmbedKGQA, and what mismatch between components does ReasoningLM set out to remove?

- **Reference answer:** 125M parameters for EmbedKGQA; the divergence in model architecture between the pre-trained language model and the GNN module, which limits knowledge sharing.
- **Evidence** (2023.emnlp-main.228, `u_4e80cf74d13c_0021`): "EmbedKGQA (Saxena et al., 2020) 125M"
- **Evidence** (2023.emnlp-main.228, `u_4e80cf74d13c_0001`): "due to the divergence in model architecture, the PLM and GNN are not closely integrated"
- **Your decision:** 

### M17: What does GEMFormer put into its memory, and how much did its best memory improve joint F1 on HotpotQA?

- **Reference answer:** It first collects relevant information over the entire document into a global memory (tokens with entropy below a threshold); the best memory improved joint F1 by 1.6 points over the highest-performing memory-free baseline on HotpotQA.
- **Evidence** (2023.emnlp-main.262, `u_2dae343019ba_0001`): "first collects relevant information over the entire document to the memory"
- **Evidence** (2023.emnlp-main.262, `u_2dae343019ba_0010`): "by 1.6 joint F1 points for HP"
- **Your decision:** 

### M18: How does Hop, Union, Generate score a set of documents, and how does it learn rationales?

- **Reference answer:** A document-set scoring function (an MLP over the document embeddings and the question); it trains with a principled probabilistic approach and needs no rationale supervision.
- **Evidence** (2023.emnlp-main.1001, `u_08db683fca63_0010`): "The document set scoring function is given by"
- **Evidence** (2023.emnlp-main.1001, `u_08db683fca63_0001`): "a principled, probabilistic approach for training explainable multi"
- **Your decision:** 

### M19: Which score is the main metric for decontextualization in the LLM experiments, and into which stages does the proposed framework split the task?

- **Reference answer:** SARI-add (the F1 of added unigram edits, with BERTScore reported too); the framework has three stages: question generation, question answering and rewriting.
- **Evidence** (2023.emnlp-main.193, `u_d352bfc2d1e1_0018`): "we report SARI-add as our performance metric"
- **Evidence** (2023.emnlp-main.193, `u_d352bfc2d1e1_0001`): "decomposes the task into three stages: question generation, question answering, and rewriting"
- **Your decision:** 

### M20: What kind of method is the deep inductive logic reasoning paper, and why does it replace the minimum t-norm?

- **Reference answer:** A deep-learning based inductive logic reasoning method; the minimum t-norm is prone to a learning plateau because the gradient flows through only one input, so it proposes a neural logic operator.
- **Evidence** (2022.acl-long.343, `u_f1e807c70065_0001`): "deep-learning based inductive logic reasoning method"
- **Evidence** (2022.acl-long.343, `u_f1e807c70065_0020`): "minimum t-norm is prone to learning plateau"
- **Your decision:** 

### M21: How many training examples does the bandit-learning study start its systems from, and how is learning from feedback cast?

- **Reference answer:** Initial models are trained on 64, 256 or 1,024 examples; learning from feedback is cast as contextual bandit learning with simulated feedback.
- **Evidence** (2022.acl-long.355, `u_e4de0d926563_0011`): "We obtain the sets of 64, 256, or 1,024"
- **Evidence** (2022.acl-long.355, `u_e4de0d926563_0001`): "We cast the problem as contextual bandit learning"
- **Your decision:** 

### M22: Which of the two approaches, the unified knowledge interface or KGT5, uses a pretrained T5-Large, and which one trains a T5-small-sized model without pretrained weights?

- **Reference answer:** The unified knowledge interface (data-to-text generator) fine-tunes the pretrained T5-Large; KGT5 uses a model with the T5-small architecture trained without the pretrained weights.
- **Evidence** (2022.acl-long.113, `u_b8cfb9072b0d_0011`): "we use the pretrained T5-Large (Raffel et al., 2020) model as our generator"
- **Evidence** (2022.acl-long.201, `u_381134ba1f9c_0021`): "a model with the same architecture as T5-small"
- **Your decision:** 

### M23: Which two datasets do both KG-FiD and the single-model open-domain QA approach (YONO) use for their experiments, and which of them builds on FiD?

- **Reference answer:** Natural Questions and TriviaQA; KG-FiD builds on and improves FiD.
- **Evidence** (2022.acl-long.340, `u_732906872c61_0027`): "Experiments on Natural Questions and TriviaQA"
- **Evidence** (2022.emnlp-main.198, `u_be1f94442adf_0018`): "Natural Questions (Kwiatkowski et al., 2019) and TriviaQA (Joshi et al., 2017)"
- **Your decision:** 

### M24: How do the long-form QA evaluation study and the open-domain QA evaluation study differ in who judges the answers?

- **Reference answer:** The long-form study hires domain experts in seven areas to give preference judgments over pairs of answers; the open-domain study evaluates the answers of 12 models on 301 sampled questions with manual evaluation.
- **Evidence** (2023.acl-long.181, `u_e84a3c72733d_0001`): "We hire domain experts in seven areas to provide preference judgments over pairs of answers"
- **Evidence** (2023.acl-long.307, `u_61676b02aa27_0010`): "assess 12 open-domain QA models"
- **Your decision:** 

### M25: Which core model does SQUIRE use to turn a query into a path, and which knowledge-graph QA paper deals with questions that have temporal intent?

- **Reference answer:** SQUIRE uses an encoder-decoder Transformer; SF-TQA (the semantic-framework approach) handles temporal questions over knowledge graphs.
- **Evidence** (2022.emnlp-main.107, `u_4724660473c3_0001`): "encoder-decoder Transformer structure to translate the query to a path"
- **Evidence** (2022.emnlp-main.122, `u_af4b5ba47ddd_0001`): "Answering factual questions with temporal intent over knowledge graphs"
- **Your decision:** 

### M26: Which two papers use counterfactuals, and for what does each use them?

- **Reference answer:** The retrieve-generate-filter paper creates counterfactual training and evaluation data; the counterfactual multi-hop QA paper uses counterfactual inference to disentangle disconnected reasoning.
- **Evidence** (2022.acl-long.117, `u_6183c13e0bb6_0001`): "create counterfactual evaluation and training data with minimal human supervision"
- **Evidence** (2023.acl-long.231, `u_d37e80b0a561_0001`): "a counterfactual inference is proposed to disentangle the disconnected reasoning"
- **Your decision:** 

### M27: Which paper simulates user feedback to cut annotation and which one studies how users react to QA answers?

- **Reference answer:** The bandit-learning paper simulates feedback from supervised data to reduce data annotation; the background-information paper studies how users interact with QA systems and over-rely on predictions.
- **Evidence** (2022.acl-long.355, `u_e4de0d926563_0001`): "analyze the characteristics of several learning scenarios with focus on reducing data annotation"
- **Evidence** (2023.emnlp-main.201, `u_71f8f712a4f8_0001`): "we study how users interact with QA systems"
- **Your decision:** 

### M28: How do KG-FiD and ReasoningLM each bring knowledge-graph structure into a text model?

- **Reference answer:** KG-FiD uses a knowledge graph to establish structural relationships among the retrieved passages; ReasoningLM makes a pre-trained language model directly support subgraph reasoning for KGQA.
- **Evidence** (2022.acl-long.340, `u_732906872c61_0001`): "uses a knowledge graph to establish the structural relationship among the retrieved passages"
- **Evidence** (2023.emnlp-main.228, `u_4e80cf74d13c_0001`): "develop a more capable PLM that can directly support subgraph reasoning for KGQA"
- **Your decision:** 

### M29: Which paper splits its task into three stages and which splits query generation into two steps?

- **Reference answer:** The decontextualization framework (question generation, question answering, rewriting); SF-TQA (constraint evocation and constraint grounding).
- **Evidence** (2023.emnlp-main.193, `u_d352bfc2d1e1_0001`): "decomposes the task into three stages: question generation, question answering, and rewriting"
- **Evidence** (2022.emnlp-main.122, `u_af4b5ba47ddd_0011`): "The query generation consists of two steps"
- **Your decision:** 

### M30: Which approach relies on a multilingual dense retriever, and which one folds the retriever into the transformer itself?

- **Reference answer:** The cross-lingual attribution study models attributed QA with CORA, whose multilingual dense retriever MDPR is based on mBERT; the single-model open-domain QA approach casts the retriever and the reranker as internal passage-wise attention mechanisms inside the transformer.
- **Evidence** (2023.emnlp-main.10, `u_60ab7f2e85b3_0008`): "multilingual dense retriever ( MDPR ) which is based on mBERT"
- **Evidence** (2022.emnlp-main.198, `u_be1f94442adf_0001`): "casting the retriever and the reranker as internal passage-wise attention mechanisms"
- **Your decision:** 
