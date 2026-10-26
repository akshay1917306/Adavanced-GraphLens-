from graphlens_pipeline.localgraph import Edge, Node, Subgraph
from graphlens_pipeline.replayexport import MAX_NODES, baseline_entry, pick_graph


def node(i, seed=False, score=0.0):
    return Node(i, i.upper(), "Method", "", [], 1, 0 if seed else 1, is_seed=seed, score=score)


def edge(a, b):
    return Edge(a, b, "USES", "", 1.0, [])


def test_seeds_and_cited_entities_come_first_and_the_graph_is_capped():
    nodes = [node("a", seed=True), node("b"), node("c", score=0.9)]
    nodes += [node(f"n{i}", score=0.5) for i in range(10)]
    edges = [edge("a", "b"), edge("a", "c")] + [edge("a", f"n{i}") for i in range(10)]
    dots, links = pick_graph(Subgraph(nodes, edges), ["b"])
    ids = [d["id"] for d in dots]
    assert ids[:2] == ["a", "b"]
    assert len(ids) == MAX_NODES
    assert all(link["source"] in ids and link["target"] in ids for link in links)


def test_a_dot_that_touches_nothing_chosen_is_not_added():
    nodes = [node("a", seed=True), node("far", score=1.0)]
    dots, links = pick_graph(Subgraph(nodes, []), [])
    assert [d["id"] for d in dots] == ["a"]
    assert links == []


def test_baseline_entry_keeps_text_only():
    entry = baseline_entry({"status": "answered", "text": "plain answer"})
    assert entry["mode"] == "baseline"
    assert entry["text"] == "plain answer"
    assert "citations" not in entry
