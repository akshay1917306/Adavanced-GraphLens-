# LatticeRank: Graph-Aware Passage Ranking for Multi-Hop Questions

**Authors:** Ilsa Kerrow, Tomas Venn
**Affiliation:** Northfield Institute of Computing
**Synthetic fixture document. All names, methods, datasets, and results are fictional.**

## Abstract

We propose LatticeRank, a passage ranking method that builds a small graph of
entities mentioned in candidate passages and ranks passages by how well they
connect the entities in a question. LatticeRank targets multi-hop question
answering, where the answer depends on facts spread over two or more passages.

## Method

LatticeRank first retrieves 50 candidate passages with BM25. It then links
entity mentions, adds an edge between two passages when they share an entity,
and scores each passage with a personalized random walk seeded by the question
entities.

## Experiments

We evaluate LatticeRank on MiraQA, a multi-hop benchmark of 4,000 questions.
LatticeRank reaches 61.2 exact match, compared with 54.8 for plain BM25 ranking.
We also report results on ChainBench, where LatticeRank reaches 47.5 exact match.

## Conclusion

Connecting passages through shared entities helps multi-hop retrieval.
Future work will combine LatticeRank with dense retrievers.
