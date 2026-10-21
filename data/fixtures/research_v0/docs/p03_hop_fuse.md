# HopFuse: Fusing Dense and Graph Signals for Retrieval

**Authors:** Tomas Venn, Ada Morrow
**Affiliation:** Northfield Institute of Computing
**Synthetic fixture document. All names, methods, datasets, and results are fictional.**

## Abstract

HopFuse combines a dense retriever with the graph score from LatticeRank. The
two scores are fused with a learned weight per question type. HopFuse improves
on LatticeRank for multi-hop question answering.

## Method

HopFuse uses DenseLite to embed passages and questions. It computes the
LatticeRank graph score for the top 100 dense results and fuses both scores
with a small logistic regression model.

## Results

On MiraQA, HopFuse reaches 65.9 exact match, which is 4.7 points above
LatticeRank. On ChainBench, HopFuse reaches 51.0 exact match.

## Related Work

This paper builds on the LatticeRank paper by Kerrow and Venn and on the
MiraQA benchmark by Saldanha and Kerrow.
