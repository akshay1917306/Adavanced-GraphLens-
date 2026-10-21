# MiraQA: A Benchmark for Questions That Need Two Documents

**Authors:** Priya Saldanha, Ilsa Kerrow
**Affiliation:** Northfield Institute of Computing; Coastline AI Lab
**Synthetic fixture document. All names, methods, datasets, and results are fictional.**

## Abstract

We introduce MiraQA, a dataset of 4,000 questions about fictional scientific
topics. Each question needs facts from exactly two source documents. MiraQA is
designed to measure multi-hop question answering and the faithfulness of
citations.

## Construction

Annotators wrote pairs of short documents and a question that can only be
answered by combining them. A second annotator checked that neither document
alone is enough.

## Baselines

We report a BM25 baseline at 54.8 exact match. A dense retriever named
DenseLite reaches 56.1 exact match on MiraQA.

## License

MiraQA is released for research use under a permissive license.
