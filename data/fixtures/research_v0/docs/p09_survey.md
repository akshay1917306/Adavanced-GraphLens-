# A Short Survey of Graph-Based Retrieval

**Authors:** Priya Saldanha
**Affiliation:** Coastline AI Lab
**Synthetic fixture document. All names, methods, datasets, and results are fictional.**

## Overview

This survey reviews graph-based retrieval methods. LatticeRank ranks passages
through shared entities. HopFuse fuses LatticeRank with the DenseLite
retriever. PathExplain explains paths between two entities. CommunityLens
summarizes communities for corpus-level questions.

## Benchmarks

MiraQA and ChainBench measure multi-hop question answering. ThemeSet measures
corpus-level summarization.

## Open problems

Entity resolution errors, such as treating "Lattice Rank" and "LatticeRank" as
two different methods, break multi-hop answers. Provenance for every edge is
needed so answers can be audited.
