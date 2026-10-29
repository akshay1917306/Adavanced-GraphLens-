import argparse, dataclasses, json, os, statistics
from pathlib import Path
from neo4j import GraphDatabase
from sqlalchemy import create_engine
from qdrant_client import QdrantClient
from graphlens_pipeline import localcontext as lc
from graphlens_pipeline.__main__ import _local_deps
from graphlens_pipeline.answer import search_passages
from graphlens_pipeline.embed import FastEmbedder
from graphlens_pipeline.localanswer import prepare_local

args = argparse.Namespace(index_version="idx2-full-g0", ontology=Path("/ontology/ontology.yaml"))
import glob; args.ontology = Path(glob.glob("/ontology/*.y*ml")[0])
engine = create_engine(os.environ["DATABASE_URL"])
qs = json.load(open("/data/eval/phase4/local_hard.json"))["questions"]
emb = FastEmbedder(); client = QdrantClient(url=os.environ["QDRANT_URL"])
orig = (dict(lc.SHARES), lc.MAX_UNIT_TOKENS, lc.CITATION_WEIGHT)

def run(name, k=6, shares=None, unit_tok=None, weight=None, plain_only_rank=False):
    lc.SHARES.clear(); lc.SHARES.update(orig[0]); lc.MAX_UNIT_TOKENS = orig[1]
    if shares: lc.SHARES.update(shares)
    if unit_tok: lc.MAX_UNIT_TOKENS = unit_tok
    cov, full, n_units = [], 0, []
    with GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])) as driver:
        deps = _local_deps(engine, driver, args, embedder=emb, client=client)
        deps = dataclasses.replace(deps, plain_hits=lambda q: [p.unit_id for p in search_passages(client, engine, emb, q, k=k)])
        if weight is not None:
            orig_assemble = lc.assemble
            import functools
            lc.assemble = functools.partial(orig_assemble, citation_weight=weight)
        try:
            for q in qs:
                want = {e["unit_id"] for e in q["evidence"]}
                early, ctx, _ = prepare_local(deps, q["question"])
                shown = {i.ref for i in ctx.items if i.label.startswith("T")} if ctx else set()
                c = len(want & shown) / len(want); cov.append(c); full += c == 1.0; n_units.append(len(shown))
        finally:
            if weight is not None: lc.assemble = orig_assemble
    print(f"{name}: gold shown {statistics.mean(cov):.0%} avg, all gold for {full}/{len(qs)}, units shown {statistics.mean(n_units):.1f}", flush=True)

import sys
mode = sys.argv[1] if len(sys.argv) > 1 else "all"
run("0 current (plain 6, units 45%, cap 450, w default)")
run("1 plain top-10", k=10)
run("2 plain top-8", k=8)
run("3 units share 60% (reports 5%)", shares={"units": 0.60, "reports": 0.05})
run("4 unit cap 300 tokens", unit_tok=300)
run("5 plain 10 + cap 300 + units 60%", k=10, unit_tok=300, shares={"units": 0.60, "reports": 0.05})
for w in (0.0, 0.3, 0.7):
    run(f"6 citation weight {w}", weight=w)
