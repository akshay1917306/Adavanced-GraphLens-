# PathExplain: Explaining Links Between Two Entities

**Authors:** Ada Morrow, Rhea Lindqvist
**Affiliation:** Coastline AI Lab; Harborview University
**Synthetic fixture document. All names, methods, datasets, and results are fictional.**

## Abstract

PathExplain finds short paths between two entities in a knowledge graph and
writes an explanation backed by the source passages for each edge. It targets
relation explanation.

## Method

PathExplain searches paths of at most three hops and ranks them by edge
confidence. It improves on HopFuse for questions that name two entities,
because it reasons about the path directly.

## Evaluation

On the two-entity subset of ChainBench, PathExplain reaches 58.3 exact match,
compared with 51.0 for HopFuse.
