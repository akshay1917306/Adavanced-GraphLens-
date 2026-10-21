# Low-fidelity wireframes (Phase 0)

Rough boxes only, to agree on layout. Colours, fonts, and real components come in
Phase 5 (blueprint Part 3). Based on blueprint sections 3.3, 3.4, and 3.7.

## 1. Ask screen (desktop, 1280 px and wider)

```
+----------------------------------------------------------------------------+
| GraphLens   [Ask] [Explore] [Compare]                    corpus v   theme  |
+--------------------------------------------+-------------------------------+
|  Mode: (Auto) Local Global Relate Baseline |  EVIDENCE PANEL               |
|  +--------------------------------------+  |  [Graph] [Passages] [Communities]
|  | Ask a question about the corpus...   |  |                               |
|  +--------------------------------------+  |   (o)---(o)                   |
|                                            |    |   \                        |
|  ANSWER (streams in)                       |   (o)  (o)---(o)              |
|  HopFuse improves on LatticeRank [1] and   |                               |
|  is evaluated on MiraQA [2] ...            |  [1] p03 HopFuse, section 3   |
|                                            |  "HopFuse reaches 65.9 ..."   |
|  Citation check: verified                  |                               |
|  [thumbs up] [thumbs down]                 |                               |
+--------------------------------------------+-------------------------------+
```

## 2. Ask screen (mobile, under 1280 px)

```
+-----------------------+
| GraphLens        menu |
| Mode: Auto v          |
| [ Ask a question... ] |
| ANSWER ...  [1] [2]   |
| [Answer][Graph][Src]  |  <- evidence becomes stacked tabs
+-----------------------+
```

## 3. Evidence graph (inside the panel)

```
+-------------------------------+
| filter: [type v] [hops: 2 v]  |
|   (Method)----IMPROVES_ON---> |
|   (Dataset) (Paper) (Task)    |
| click a node -> NodeDrawer:   |
|   name, type, aliases,        |
|   source passages             |
+-------------------------------+
```

## 4. Explore

```
+----------------------------+----------------------------------+
| Community tree             | Community report                 |
|  > Level 0                 |  Title, summary, findings        |
|    > Graph retrieval       |  Entities: LatticeRank, HopFuse  |
|    > Global summarization  |  Source passages                 |
| [search entities...]       |                                  |
+----------------------------+----------------------------------+
```

## 5. Admin run detail (admin key required)

```
+--------------------------------------------------------------+
| Run 2026-10-21-01   status: running   cost: $0.42 / cap $5    |
| ingest [done] chunk [done] extract [####----] resolve [ ] ... |
| Quality gate: duplicates 2% ok | orphans 0% ok | provenance ok|
| [Publish] (enabled only when every gate check passes)        |
+--------------------------------------------------------------+
```
