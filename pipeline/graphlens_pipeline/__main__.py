"""Command line for the pipeline.

docker compose run --rm pipeline ingest
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine

from graphlens_pipeline.embed import MAX_INPUT_TOKENS
from graphlens_pipeline.ingest import ingest_manifest

DEFAULT_CORPUS = "qa_v0 (ACL Anthology QA papers)"
DEFAULT_ONTOLOGY = Path("/ontology/research_v2.yaml")  # version 2: see decision D24
DEFAULT_DESCRIPTION = "Question answering papers, ACL and EMNLP 2022-2023, CC BY 4.0"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="graphlens_pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="parse, chunk and store the papers of a manifest")
    ingest.add_argument("--manifest", type=Path, default=Path("/data/corpus/qa_v0/manifest.csv"))
    ingest.add_argument("--pdf-dir", type=Path, default=Path("/data/corpus/qa_v0/pdfs"))
    ingest.add_argument("--corpus-name", default=DEFAULT_CORPUS)
    embed = sub.add_parser("embed", help="embed text units into Qdrant (local models, no cost)")
    embed.add_argument("--corpus-name", default=DEFAULT_CORPUS)
    embed.add_argument("--corpus-slug", default="qa_v0")
    embed.add_argument("--index-version", default="baseline-1")
    embed.add_argument("--batch-size", type=int, default=32)
    embed.add_argument("--no-live", action="store_true", help="do not move the units_live alias")
    ask = sub.add_parser(
        "ask", help="answer one question with plain RAG (calls OpenAI, costs money)"
    )
    ask.add_argument("question")
    ask.add_argument("--k", type=int, default=6, help="how many passages to retrieve")
    eval_dir = Path("/data/eval/v0")
    check = sub.add_parser(
        "eval-verify", help="check that every evidence quote exists in the corpus"
    )
    check.add_argument("--questions", type=Path, default=eval_dir / "questions.json")
    check.add_argument("--local", type=int, default=30, help="expected number of local questions")
    check.add_argument("--global", dest="global_count", type=int, default=10,
                       help="expected number of global questions")  # fmt: skip
    review = sub.add_parser("eval-review", help="write the review page for the owner")
    review.add_argument("--questions", type=Path, default=eval_dir / "questions.json")
    review.add_argument("--out", type=Path, default=Path("/tmp/REVIEW.md"))  # noqa: S108
    index = sub.add_parser("index", help="run the whole flow: ingest, then embed (no OpenAI cost)")
    index.add_argument("--manifest", type=Path, default=Path("/data/corpus/qa_v0/manifest.csv"))
    index.add_argument("--pdf-dir", type=Path, default=Path("/data/corpus/qa_v0/pdfs"))
    index.add_argument("--corpus-name", default=DEFAULT_CORPUS)
    index.add_argument("--corpus-slug", default="qa_v0")
    index.add_argument("--index-version", default="baseline-1")
    estimate = sub.add_parser("extract-estimate", help="estimate extraction cost, calls no model")
    estimate.add_argument("--corpus-name", default=DEFAULT_CORPUS)
    extract = sub.add_parser(
        "extract", help="extract entities and relations (calls OpenAI, costs money)"
    )
    extract.add_argument("--corpus-name", default=DEFAULT_CORPUS)
    extract.add_argument("--sample", type=float, default=0.05, help="share of units, 1 = all")
    extract.add_argument("--gleaning", type=int, default=0, help="extra passes for missed items")
    extract.add_argument("--max-cost-usd", type=float, default=0.25, help="stop when spent")
    extract.add_argument("--workers", type=int, default=4)
    extract.add_argument("--index-version", default="idx-sample-1")
    extract.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    resolve = sub.add_parser("resolve", help="merge duplicate entities (small model cost, capped)")
    resolve.add_argument("--corpus-name", default=DEFAULT_CORPUS)
    resolve.add_argument("--index-version", default="idx2-full-g0")
    resolve.add_argument("--gleaning", type=int, default=0)
    resolve.add_argument("--max-cost-usd", type=float, default=0.25)
    resolve.add_argument("--no-llm", action="store_true", help="never ask the model")
    resolve.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    graph = sub.add_parser(
        "graph-load", help="resolve (cached answers) and load the graph into Neo4j"
    )
    graph.add_argument("--corpus-name", default=DEFAULT_CORPUS)
    graph.add_argument("--index-version", default="idx2-full-g0")
    graph.add_argument("--gleaning", type=int, default=0)
    graph.add_argument("--max-cost-usd", type=float, default=0.25)
    graph.add_argument("--no-llm", action="store_true", help="never ask the model")
    graph.add_argument(
        "--keep-isolated", action="store_true",
        help="also load entities that have no relation and were mentioned once",
    )  # fmt: skip
    graph.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    quality = sub.add_parser(
        "quality-report", help="measure the graph quality checks (no model, no cost)"
    )
    quality.add_argument("--index-version", default="idx2-full-g0")
    quality.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    quality.add_argument("--out", type=Path, default=None, help="write the report here")
    comm = sub.add_parser(
        "communities", help="find hierarchical communities and write them to Neo4j (no cost)"
    )
    comm.add_argument("--index-version", default="idx2-full-g0")
    comm.add_argument("--max-cluster-size", type=int, default=50)
    comm.add_argument("--seed", type=int, default=42)
    rep = sub.add_parser(
        "community-reports", help="write a report for every community (calls OpenAI, costs money)"
    )
    rep.add_argument("--corpus-name", default=DEFAULT_CORPUS)
    rep.add_argument("--index-version", default="idx2-full-g0", help="the graph to read")
    rep.add_argument("--run-version", default="idx2-full-g0-reports")
    rep.add_argument("--max-cost-usd", type=float, default=0.75, help="stop when spent")
    rep.add_argument("--workers", type=int, default=4)
    rep.add_argument("--dry-run", action="store_true", help="estimate the cost, call no model")
    rep.add_argument(
        "--smoke", type=int, default=0, help="only N leaf communities, print them, store nothing"
    )
    cembed = sub.add_parser(
        "community-embed", help="embed the community reports into Neo4j (local model, no cost)"
    )
    cembed.add_argument("--index-version", default="idx2-full-g0")
    cquality = sub.add_parser(
        "community-quality", help="measure the Phase 3 gate checks (no model, no cost)"
    )
    cquality.add_argument("--index-version", default="idx2-full-g0")
    cquality.add_argument("--run-version", default="idx2-full-g0-reports")
    gask = sub.add_parser(
        "global-ask", help="answer a corpus-wide question from community reports (costs money)"
    )
    gask.add_argument("question")
    gask.add_argument("--index-version", default="idx2-full-g0")
    gask.add_argument("--level", type=int, default=1)
    gask.add_argument("--max-reports", type=int, default=40)
    gask.add_argument("--threshold", type=float, default=None)
    gask.add_argument("--no-dynamic", action="store_true", help="use every report of the level")
    gask.add_argument(
        "--select-only", action="store_true", help="show the selection, call no model"
    )
    geval = sub.add_parser(
        "global-eval", help="judge global search against the baseline (calls OpenAI, costs money)"
    )
    geval.add_argument("--index-version", default="idx2-full-g0")
    geval.add_argument(
        "--questions", type=Path, nargs="+",
        default=[eval_dir / "questions.json", eval_dir / "global_extra.json"],
    )  # fmt: skip
    geval.add_argument("--ablation-questions", type=int, default=10,
                       help="how many questions also run without dynamic selection")  # fmt: skip
    geval.add_argument("--max-cost-usd", type=float, default=1.0)
    geval.add_argument("--dry-run", action="store_true", help="estimate the cost, call no model")
    geval.add_argument("--out-dir", type=Path, default=Path("/out"))
    geval.add_argument("--label", default="")
    link = sub.add_parser(
        "link-entities", help="show which entities a question links to (local, no cost)"
    )
    link.add_argument("question", nargs="*")
    link.add_argument("--index-version", default="idx2-full-g0")
    link.add_argument("--min-vector-score", type=float, default=0.79)
    link.add_argument(
        "--file", type=Path, default=None, help="a questions.json: link every question"
    )
    lgraph = sub.add_parser(
        "local-graph-eval",
        help="free ablation: how many evidence units each retrieval step reaches (no model)",
    )
    lgraph.add_argument("--index-version", default="idx2-full-g0")
    lgraph.add_argument("--questions", type=Path, default=eval_dir / "questions.json")
    lgraph.add_argument("--kind", default="local")
    lgraph.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    lctx = sub.add_parser(
        "local-context", help="show the context local search would send (no model, no cost)"
    )
    lctx.add_argument("question")
    lctx.add_argument("--index-version", default="idx2-full-g0")
    lctx.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    lctx.add_argument("--show", action="store_true", help="print the whole prompt text")
    lask = sub.add_parser(
        "local-ask", help="answer a specific question from the graph (about half a cent)"
    )
    lask.add_argument("question")
    lask.add_argument("--index-version", default="idx2-full-g0")
    lask.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    lask.add_argument("--show-context", action="store_true")
    rel = sub.add_parser(
        "relate",
        help="how are two things connected? (paths are free; the explanation costs ~0.3 cent)",
    )
    rel.add_argument("question")
    rel.add_argument("--index-version", default="idx2-full-g0")
    rel.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    rel.add_argument("--paths-only", action="store_true", help="find paths, call no model")
    rexp = sub.add_parser(
        "export-replay",
        help="build the saved-answer file for the UI from a finished evaluation (no model, free)",
    )
    rexp.add_argument("--eval-json", type=Path, required=True)
    rexp.add_argument("--questions", type=Path, required=True, help="local_hard.json")
    rexp.add_argument("--unanswerable", type=Path, required=True, help="unanswerable.json")
    rexp.add_argument("--out", type=Path, required=True)
    rexp.add_argument("--count", type=int, default=5, help="how many answered questions")
    rexp.add_argument("--refuse", nargs="*", default=["U01", "U05"], help="unanswerable ids")
    rexp.add_argument("--index-version", default="idx2-full-g0")
    rexp.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    ask_any = sub.add_parser(
        "ask-auto", help="pick the right mode and answer (local, global, relate or baseline)"
    )
    ask_any.add_argument("question")
    ask_any.add_argument("--mode", choices=["local", "global", "relate", "baseline"], default=None)
    ask_any.add_argument("--index-version", default="idx2-full-g0")
    ask_any.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    ask_any.add_argument(
        "--route-only", action="store_true", help="show the chosen mode, answer nothing"
    )
    reval = sub.add_parser(
        "route-eval", help="router accuracy on labeled questions, rules only (no model, no cost)"
    )
    reval.add_argument("--index-version", default="idx2-full-g0")
    reval.add_argument(
        "--questions", type=Path, nargs="+", default=[eval_dir / "questions.json"],
    )  # fmt: skip
    reval.add_argument("--show-misses", action="store_true")
    p4 = sub.add_parser(
        "review-phase4", help="write the review pages for the new Phase 4 question sets (no cost)"
    )
    p4.add_argument("--dir", type=Path, default=Path("/data/eval/phase4"))
    p4.add_argument("--out-dir", type=Path, default=Path("/out"))
    leval = sub.add_parser(
        "local-eval", help="the small paid Phase 4 evaluation (about $0.4; use --dry-run first)"
    )
    leval.add_argument("--index-version", default="idx2-full-g0")
    leval.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    leval.add_argument("--dir", type=Path, default=Path("/data/eval/phase4"))
    leval.add_argument("--out-dir", type=Path, default=Path("/out"))
    leval.add_argument("--max-cost-usd", type=float, default=0.6)
    leval.add_argument("--dry-run", action="store_true")
    leval.add_argument("--label", default="")
    bench = sub.add_parser(
        "global-bench", help="time and price fresh global searches, no cache (costs money)"
    )
    bench.add_argument("--index-version", default="idx2-full-g0")
    bench.add_argument("--questions", type=Path, default=eval_dir / "questions.json")
    bench.add_argument("--n", type=int, default=10)
    bench.add_argument("--no-dynamic", action="store_true", help="use every report of the level")
    bench.add_argument("--max-cost-usd", type=float, default=0.5)
    bench.add_argument("--dry-run", action="store_true", help="estimate the cost, call no model")
    sheets = sub.add_parser(
        "review-sheets", help="write the Phase 3 review pages for the owner (no model, no cost)"
    )
    sheets.add_argument("--index-version", default="idx2-full-g0")
    sheets.add_argument("--results", type=Path, default=eval_dir / "results/global-phase3.json")
    sheets.add_argument("--out-dir", type=Path, default=Path("/out"))
    for name, helptext in (
        ("labels-draw", "draw the samples for labeling (refuses to overwrite existing files)"),
        ("labels-render", "write the review pages from the label files"),
        ("labels-score", "score relation precision and entity-resolution F1 from the labels"),
    ):
        labels = sub.add_parser(name, help=helptext)
        labels.add_argument("--dir", type=Path, default=Path("/labels"))
        labels.add_argument("--corpus-name", default=DEFAULT_CORPUS)
        labels.add_argument("--index-version", default="idx2-full-g0")
        labels.add_argument("--gleaning", type=int, default=0)
        labels.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
        labels.add_argument(
            "--refresh-decisions", action="store_true",
            help="before scoring, use the resolver's current decision for each labeled pair",
        )  # fmt: skip
    load = sub.add_parser("eval-load", help="store the approved questions in the database")
    load.add_argument("--questions", type=Path, default=eval_dir / "questions.json")
    load.add_argument("--version", type=int, default=2, help="evaluation set version to create")
    remap = sub.add_parser("eval-remap", help="point evidence at the current text unit IDs")
    remap.add_argument("--questions", type=Path, default=eval_dir / "questions.json")
    remap.add_argument("--out", type=Path, default=Path("/out/questions.json"))
    run = sub.add_parser("eval-run", help="run the baseline on the evaluation set and score it")
    run.add_argument("--questions", type=Path, default=eval_dir / "questions.json")
    run.add_argument("--dry-run", action="store_true", help="estimate the cost, call no model")
    run.add_argument("--max-cost-usd", type=float, default=0.25, help="stop when this is spent")
    run.add_argument("--out-dir", type=Path, default=Path("/out"))
    args = parser.parse_args(argv)

    if args.command == "eval-review":
        from graphlens_pipeline.evalset import load_questions, render_review

        args.out.write_text(render_review(load_questions(args.questions)), encoding="utf-8")
        print(f"Wrote {args.out}")
        return 0

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 2
    engine = create_engine(database_url)  # the URL is never printed

    if args.command == "index":
        qdrant_url = os.environ.get("QDRANT_URL")
        if not qdrant_url:
            print("QDRANT_URL is not set.", file=sys.stderr)
            return 2
        from graphlens_pipeline.flow import index_baseline

        summary = index_baseline(
            database_url, qdrant_url, str(args.manifest), str(args.pdf_dir), args.corpus_name,
            DEFAULT_DESCRIPTION, args.corpus_slug, args.index_version,
        )  # fmt: skip
        ingest, embed = summary["ingest"], summary["embed"]
        print(
            f"INDEX DONE: ingest {ingest['ingested']} new / {ingest['skipped']} present "
            f"({ingest['text_units']} units); embed {embed['embedded']} new / "
            f"{embed['skipped']} present into {embed['collection']}."
        )
        for paper_id, reason in ingest["failures"].items():
            print(f"FAILED {paper_id}: {reason}", file=sys.stderr)
        return 1 if ingest["failures"] else 0

    if args.command == "resolve":
        return _resolve(engine, args)

    if args.command == "graph-load":
        return _graph_load(engine, args)

    if args.command == "quality-report":
        return _quality_report(engine, args)

    if args.command == "communities":
        return _communities(args)

    if args.command == "community-reports":
        return _community_reports(engine, args)

    if args.command == "community-embed":
        return _community_embed(args)

    if args.command == "global-ask":
        return _global_ask(args)

    if args.command == "global-eval":
        return _global_eval(engine, args)

    if args.command == "review-sheets":
        return _review_sheets(args)

    if args.command == "global-bench":
        return _global_bench(args)

    if args.command == "link-entities":
        return _link_entities(args)

    if args.command == "local-context":
        return _local_context(engine, args)

    if args.command == "local-ask":
        return _local_ask(engine, args)

    if args.command == "relate":
        return _relate(engine, args)

    if args.command == "export-replay":
        return _export_replay(engine, args)

    if args.command == "ask-auto":
        return _ask_auto(engine, args)

    if args.command == "route-eval":
        return _route_eval(args)

    if args.command == "local-eval":
        return _local_eval(engine, args)

    if args.command == "review-phase4":
        return _review_phase4(args)

    if args.command == "local-graph-eval":
        return _local_graph_eval(engine, args)

    if args.command == "community-quality":
        return _community_quality(engine, args)

    if args.command.startswith("labels-"):
        return _labels(engine, args)

    if args.command == "extract-estimate":
        return _extract_estimate(engine, args)

    if args.command == "extract":
        return _extract(engine, args)

    if args.command == "eval-load":
        from graphlens_pipeline.evalrun import load_eval_sets
        from graphlens_pipeline.evalset import load_questions

        loaded = load_eval_sets(engine, load_questions(args.questions), args.version)
        for name, count in loaded.items():
            state = "already present" if count == 0 else f"{count} questions loaded"
            print(f"{name} v{args.version}: {state}")
        return 0

    if args.command == "eval-remap":
        import json

        from graphlens_pipeline.evalset import fetch_units_by_paper, load_questions, remap_evidence

        document = json.loads(args.questions.read_text(encoding="utf-8"))
        remapped, problems = remap_evidence(
            load_questions(args.questions), fetch_units_by_paper(engine)
        )
        for problem in problems:
            print(f"PROBLEM {problem.question_id}: {problem.message}", file=sys.stderr)
        if problems:
            return 1
        document["questions"] = remapped
        document["note"] = (
            document.get("note", "") + " Unit IDs were remapped by quote after CR-0003."
        ).strip()
        args.out.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", "utf-8")
        print(f"Remapped {len(remapped)} questions into {args.out}")
        return 0

    if args.command == "eval-run":
        return _eval_run(engine, args)

    if args.command == "eval-verify":
        from graphlens_pipeline.evalset import fetch_unit_texts, load_questions, verify

        questions = load_questions(args.questions)
        wanted = {item["unit_id"] for q in questions for item in q["evidence"]}
        expected = {"local": args.local, "global": args.global_count}
        problems = verify(questions, fetch_unit_texts(engine, wanted), expected)
        for problem in problems:
            print(f"PROBLEM {problem.question_id}: {problem.message}", file=sys.stderr)
        print(f"{len(questions)} questions, {len(wanted)} evidence units, {len(problems)} problems")
        return 1 if problems else 0

    if args.command == "ask":
        return _ask(engine, args.question, args.k)

    if args.command == "embed":
        qdrant_url = os.environ.get("QDRANT_URL")
        if not qdrant_url:
            print("QDRANT_URL is not set.", file=sys.stderr)
            return 2
        from qdrant_client import QdrantClient

        from graphlens_pipeline.embed import FastEmbedder, embed_corpus

        result = embed_corpus(
            engine,
            QdrantClient(url=qdrant_url),
            args.corpus_name,
            args.corpus_slug,
            args.index_version,
            FastEmbedder(),
            batch_size=args.batch_size,
            make_live=not args.no_live,
        )
        print(
            f"Collection {result.collection}: embedded {result.embedded}, "
            f"skipped {result.skipped} already present, "
            f"{result.truncated} units longer than {MAX_INPUT_TOKENS} model tokens (tail cut)."
        )
        return 0

    report = ingest_manifest(
        engine, args.manifest, args.pdf_dir, args.corpus_name, DEFAULT_DESCRIPTION
    )
    print(
        f"Ingested {report.ingested} new documents ({report.text_units} text units); "
        f"skipped {report.skipped_duplicates} already present."
    )
    for paper_id, reason in report.failures.items():
        print(f"FAILED {paper_id}: {reason}", file=sys.stderr)
    return 1 if report.failures else 0


def _compute_resolution(engine, args):
    """Resolve the cached extraction. Returns (resolution, ontology, embedder) or an exit code."""
    from graphlens_pipeline.embed import FastEmbedder
    from graphlens_pipeline.extract import load_cached_results, load_units
    from graphlens_pipeline.llm import LlmError, OpenAiLlm
    from graphlens_pipeline.ontology import load_ontology
    from graphlens_pipeline.resolve import resolve

    ontology = load_ontology(args.ontology)
    model = os.environ.get("LLM_MODEL_SMALL") or "gpt-4.1-mini"
    units = load_units(engine, args.corpus_name)
    results = load_cached_results(engine, units, model, ontology, args.gleaning)
    if len(results) < len(units):
        print(f"Only {len(results)} of {len(units)} units are extracted; run extract first.",
              file=sys.stderr)  # fmt: skip
        return 1
    llm = None
    if not args.no_llm:
        try:
            llm = OpenAiLlm(model=model)
        except LlmError as error:
            print(f"Cannot start: {error}", file=sys.stderr)
            return 2
    embedder = FastEmbedder()
    result = resolve(
        engine, results, {u["id"]: u["title"] for u in units}, ontology, embedder.dense, llm,
        args.max_cost_usd,
    )  # fmt: skip
    return result, ontology, embedder


def _graph_load(engine, args) -> int:
    import json

    from neo4j import GraphDatabase

    from graphlens_pipeline.graphstore import (
        GraphLoadError,
        apply_schema,
        embedding_text,
        isolated_entities,
        load_graph,
        split_isolated,
    )
    from graphlens_pipeline.quality import Check, save_checks

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    computed = _compute_resolution(engine, args)
    if isinstance(computed, int):
        return computed
    result, ontology, embedder = computed
    full_count = len(result.entities)
    isolated = isolated_entities(result)
    left_out = []
    if not args.keep_isolated:
        result, left_out = split_isolated(result)
    texts = [embedding_text(e.name, e.description) for e in result.entities]
    vectors = dict(zip((e.id for e in result.entities), embedder.dense(texts), strict=True))
    try:
        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            applied = apply_schema(driver)
            counts = load_graph(driver, result, ontology, vectors, args.index_version)
    except GraphLoadError as error:
        print(f"Graph load refused: {error}", file=sys.stderr)
        return 1
    # The orphan rate BEFORE leaving anything out stays on record, so the gate cannot be gamed.
    from collections import Counter

    from sqlalchemy import text

    with engine.connect() as conn:
        run = conn.execute(
            text("SELECT id FROM index_runs WHERE index_version = :v"), {"v": args.index_version}
        ).first()
    if run:
        save_checks(engine, str(run[0]), [Check(
            "orphan_rate_before_pruning", len(isolated) / max(full_count, 1), 0.10, False,
            {"isolated": len(isolated), "entities": full_count,
             "by_type": dict(Counter(e.type for e in isolated)),
             "left_out_of_the_graph": len(left_out),
             "examples_left_out": [f"{e.type}: {e.name}" for e in left_out[:30]]},
        )])  # fmt: skip
    print(json.dumps({
        "left_out_isolated_single_mention": len(left_out),
        "schema_scripts_applied_now": applied,
        "expected": {"entities": len(result.entities), "relations": len(result.relations)},
        "in_neo4j": {
            "entities": counts.entities, "by_type": counts.entities_by_type,
            "relations": counts.relations, "by_predicate": counts.relations_by_predicate,
            "with_embedding": counts.with_embedding,
        },
        "counts_match": (counts.entities, counts.relations)
        == (len(result.entities), len(result.relations)),
    }, indent=2))  # fmt: skip
    return 0


def _communities(args) -> int:
    import json

    from neo4j import GraphDatabase

    from graphlens_pipeline.communities import (
        detect,
        read_communities,
        read_entity_graph,
        summary,
        verify_hierarchy,
        write_communities,
    )
    from graphlens_pipeline.graphstore import apply_schema

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        apply_schema(driver)
        entities, edges = read_entity_graph(driver, args.index_version)
        if not entities:
            print("The graph is empty; run graph-load first.", file=sys.stderr)
            return 1
        ids = [e["id"] for e in entities]
        found = detect(ids, edges, args.max_cluster_size, args.seed)
        problems = verify_hierarchy(found, ids)
        if problems:
            print("Hierarchy problems, nothing written:", *problems, sep=chr(10), file=sys.stderr)
            return 1
        write_communities(driver, found, args.index_version, args.seed, args.max_cluster_size)
        stored = read_communities(driver, args.index_version)
    stored_problems = verify_hierarchy(stored, ids)
    print(json.dumps({
        **summary(found), "seed": args.seed, "max_cluster_size": args.max_cluster_size,
        "stored_matches": [(c.id, c.members) for c in stored]
        == [(c.id, c.members) for c in found],
        "problems_after_write": stored_problems,
    }, indent=2))  # fmt: skip
    return 1 if stored_problems else 0


def _community_reports(engine, args) -> int:
    import json

    import tiktoken
    from neo4j import GraphDatabase

    from graphlens_pipeline.communities import read_communities
    from graphlens_pipeline.llm import LlmError, OpenAiLlm
    from graphlens_pipeline.reports import (
        PROMPT_VERSION,
        build_reports,
        estimate,
        read_graph_data,
        store_reports,
    )
    from graphlens_pipeline.runs import begin_stage, end_stage, finish_run, start_run

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    model = os.environ.get("LLM_MODEL_SMALL") or "gpt-4.1-mini"
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        communities = read_communities(driver, args.index_version)
        graph = read_graph_data(driver, args.index_version)
        if not communities:
            print("No communities; run the communities command first.", file=sys.stderr)
            return 1
        if args.dry_run:
            encoder = tiktoken.get_encoding("o200k_base")
            print(json.dumps(
                estimate(engine, model, communities, graph, lambda s: len(encoder.encode(s))),
                indent=2,
            ))  # fmt: skip
            print("Prompt tokens are counted for leaf communities and assumed for parents;")
            print("answer sizes are assumptions. Nothing was spent.")
            return 0
        try:
            llm = OpenAiLlm(model=model)
        except LlmError as error:
            print(f"Cannot start: {error}", file=sys.stderr)
            return 2
        if args.smoke:  # a few real calls to look at the quality; the answers are cached
            leaves = sorted(
                (c for c in communities if c.is_leaf and not c.is_stub), key=lambda c: c.id
            )
            step = max(1, len(leaves) // args.smoke)
            picked = leaves[::step][: args.smoke]
            result = build_reports(engine, llm, picked, graph, args.max_cost_usd, args.workers)
            for community in picked:
                report = result.reports.get(community.id)
                print(json.dumps({"community": community.id, "size": community.size,
                                  "report": report.to_json() if report else result.failed},
                                 indent=1, ensure_ascii=False))  # fmt: skip
            print(f"cost ${result.cost_usd:.4f}, calls {result.generated}, stored nothing")
            return 0
        config = {"model": model, "prompt": PROMPT_VERSION, "graph": args.index_version}
        run = start_run(
            engine, args.corpus_name, args.run_version, config, args.max_cost_usd, sample=False
        )
        begin_stage(engine, run, "community_reports", len(communities))
        result = build_reports(
            engine, llm, communities, graph, args.max_cost_usd, args.workers,
            on_progress=lambda done, total, cost: print(f"  {done}/{total} reports, ${cost:.4f}"),
        )  # fmt: skip
        store_reports(driver, result.reports, args.index_version)
    complete = len(result.reports) == len(communities)
    stats = {
        "communities": len(communities), "reports": len(result.reports),
        "generated": result.generated, "from_cache": result.from_cache, "stubs": result.stubs,
        "failed": result.failed, "skipped_by_cap": result.skipped_by_cap,
        "dropped_citations": result.dropped_citations,
        "outcome": "complete" if complete else "partial",
    }  # fmt: skip
    end_stage(engine, run, "community_reports", len(result.reports), result.cost_usd,
              None if complete else "not every community has a report")  # fmt: skip
    finish_run(engine, run, "running" if complete else "failed", result.cost_usd,
               result.tokens_in, result.tokens_out, stats)  # fmt: skip
    print(json.dumps({**stats, "cost_usd": result.cost_usd}, indent=2))
    return 0 if complete else 1


def _local_graph_eval(engine, args) -> int:
    import json
    import statistics

    from neo4j import GraphDatabase

    from graphlens_pipeline.embed import FastEmbedder
    from graphlens_pipeline.linking import EntityIndex, link_question
    from graphlens_pipeline.localgraph import (
        build_subgraph,
        evidence_coverage,
        seeds_only_subgraph,
    )
    from graphlens_pipeline.ontology import load_ontology

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    predicates = load_ontology(args.ontology).predicate_names
    questions = [
        q
        for q in json.loads(args.questions.read_text(encoding="utf-8"))["questions"]
        if q["kind"] == args.kind
    ]
    embedder = FastEmbedder()
    from qdrant_client import QdrantClient

    from graphlens_pipeline.answer import search_passages

    qdrant = QdrantClient(url=os.environ["QDRANT_URL"])
    variants = {
        "0 plain RAG baseline (6 passages)": [],
        "1 entity linking only": [],
        "2 + expansion (2 hops, ranked by similarity)": [],
        "3 + personalized PageRank": [],
        "4 + budgeted context (text units really shown)": [],
    }
    seed_hits = []
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        from graphlens_pipeline.localanswer import prepare_local

        deps = _local_deps(engine, driver, args)
        index = EntityIndex.from_neo4j(driver, args.index_version)
        for q in questions:
            wanted = {e["unit_id"] for e in q["evidence"]}
            link = link_question(
                driver, embedder.dense_query, index, q["question"], args.index_version
            )
            vector = embedder.dense_query(link.question)
            seed_hits.append(len(link.seeds) > 0)
            passages = search_passages(qdrant, engine, embedder, q["question"], k=6)
            base_hit = len(wanted & {p.unit_id for p in passages}) / len(wanted)
            variants["0 plain RAG baseline (6 passages)"].append((base_hit, len(passages)))
            rungs = [
                seeds_only_subgraph(driver, link.seeds),
                build_subgraph(driver, link.seeds, vector, predicates, args.index_version,
                               use_pagerank=False),
                build_subgraph(driver, link.seeds, vector, predicates, args.index_version),
            ]  # fmt: skip
            early, context, _ = prepare_local(deps, q["question"])
            shown = {i.ref for i in context.items if i.label.startswith("T")} if context else set()
            variants["4 + budgeted context (text units really shown)"].append(
                (len(wanted & shown) / len(wanted), len(shown))
            )
            for name, graph in zip(list(variants)[1:4], rungs, strict=True):
                variants[name].append((evidence_coverage(graph, wanted), len(graph.nodes)))
    print(f"{len(questions)} {args.kind} questions; share of gold evidence units reached")
    print("  (the baseline row counts text units; the graph rows count nodes)")
    for name, rows in variants.items():
        coverage = statistics.mean(c for c, _ in rows)
        full = sum(1 for c, _ in rows if c == 1.0)
        nodes = statistics.mean(n for _, n in rows)
        print(
            f"  {name}: {coverage:.0%} on average, all units reached for {full}, {nodes:.0f} nodes"
        )
    print(f"  questions with at least one seed: {sum(seed_hits)} of {len(seed_hits)}")
    return 0


def _local_deps(engine, driver, args):
    """Local search wired to the real databases and the local embedding model."""
    import tiktoken
    from qdrant_client import QdrantClient

    from graphlens_pipeline.answer import search_passages
    from graphlens_pipeline.embed import LIVE_ALIAS, FastEmbedder
    from graphlens_pipeline.linking import EntityIndex, link_question
    from graphlens_pipeline.localanswer import LocalDeps
    from graphlens_pipeline.localcontext import (
        postgres_unit_rows,
        qdrant_unit_vectors,
        seed_reports,
        similarity_to_question,
    )
    from graphlens_pipeline.localgraph import build_subgraph
    from graphlens_pipeline.ontology import load_ontology

    encoder = tiktoken.get_encoding("o200k_base")
    embedder = FastEmbedder()
    client = QdrantClient(url=os.environ["QDRANT_URL"])
    predicates = load_ontology(args.ontology).predicate_names
    index = EntityIndex.from_neo4j(driver, args.index_version)
    return LocalDeps(
        link=lambda q: link_question(driver, embedder.dense_query, index, q, args.index_version),
        subgraph=lambda lk: build_subgraph(
            driver, lk.seeds, embedder.dense_query(lk.question), predicates, args.index_version
        ),
        reports=lambda lk: seed_reports(driver, lk.seeds, args.index_version),
        unit_rows=lambda ids: postgres_unit_rows(engine, ids),
        unit_similarity=lambda lk, ids: similarity_to_question(
            embedder.dense_query(lk.question), qdrant_unit_vectors(client, ids, LIVE_ALIAS)
        ),
        count_tokens=lambda s: len(encoder.encode(s)),
        index=index,
        plain_hits=lambda q: [p.unit_id for p in search_passages(client, engine, embedder, q, k=6)],
    )


def _review_phase4(args) -> int:
    import json

    from graphlens_pipeline.evalset import render_review
    from graphlens_pipeline.reviewsheets import render_relate_review, render_unanswerable_review

    def load(name: str) -> list[dict]:
        return json.loads((args.dir / name).read_text(encoding="utf-8"))["questions"]

    (args.out_dir / "REVIEW_LOCAL_HARD.md").write_text(
        render_review(load("local_hard.json")), encoding="utf-8"
    )
    (args.out_dir / "REVIEW_RELATE.md").write_text(
        render_relate_review(load("relate_pairs.json")), encoding="utf-8"
    )
    (args.out_dir / "REVIEW_UNANSWERABLE.md").write_text(
        render_unanswerable_review(load("unanswerable.json")), encoding="utf-8"
    )
    print("wrote REVIEW_LOCAL_HARD.md, REVIEW_RELATE.md, REVIEW_UNANSWERABLE.md")
    return 0


def _local_eval(engine, args) -> int:
    """The lean paid evaluation of Phase 4 (see localeval.py). --dry-run only estimates."""
    import dataclasses
    import json
    import time
    from datetime import date

    import tiktoken
    from neo4j import GraphDatabase
    from qdrant_client import QdrantClient

    from graphlens_pipeline.answer import AnswerError, answer_question
    from graphlens_pipeline.embed import FastEmbedder
    from graphlens_pipeline.globalsearch import select_communities
    from graphlens_pipeline.llm import LlmError, OpenAiLlm
    from graphlens_pipeline.localanswer import answer_local
    from graphlens_pipeline.localcontext import postgres_unit_rows
    from graphlens_pipeline.localeval import (
        AnswerRecord,
        check_support,
        paired,
        refusal_accuracy,
        run_correctness,
        summarize,
        support_sample,
    )
    from graphlens_pipeline.ontology import load_ontology
    from graphlens_pipeline.relate import answer_relate
    from graphlens_pipeline.router import route_question

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password and os.environ.get("QDRANT_URL")):
        print("NEO4J_* and QDRANT_URL must be set.", file=sys.stderr)
        return 2

    def load(path):
        return json.loads(path.read_text(encoding="utf-8"))["questions"]

    hard = load(args.dir / "local_hard.json")
    unanswerable = load(args.dir / "unanswerable.json")
    pairs = load(args.dir / "relate_pairs.json")
    n_hard, n_un, n_rel = len(hard), len(unanswerable), len(pairs)
    # per-call prices checked on real calls: a local answer about $0.0035, a baseline answer
    # $0.0013, a judge call $0.0004, a support check $0.001, a relate explanation $0.0016
    estimate = (
        n_hard * (0.0013 + 2 * 0.0035) + 3 * n_hard * 0.0004 + 20 * 0.001
        + n_un * 0.5 * 0.0035 + n_rel * 0.0016 + 80 * 0.3 * 0.0003
    )  # fmt: skip
    if args.dry_run:
        print(json.dumps({
            "hard_questions": n_hard, "systems": 3, "answers": 3 * n_hard,
            "correctness_judgements": 3 * n_hard, "support_checks": 20,
            "unanswerable_questions": n_un, "relate_pairs": n_rel,
            "cost_usd_estimate": round(estimate, 3),
            "cost_usd_with_margin": round(estimate * 1.4, 3),
        }, indent=2))  # fmt: skip
        print("Per-call prices come from real calls; nothing was spent.")
        return 0

    llm = OpenAiLlm(model=os.environ.get("LLM_MODEL_SMALL") or None)
    encoder = tiktoken.get_encoding("o200k_base")
    predicates = load_ontology(args.ontology).predicate_names
    qdrant = QdrantClient(url=os.environ["QDRANT_URL"])
    embedder = FastEmbedder()
    spent = 0.0
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        deps = _local_deps(engine, driver, args)
        index = deps.index
        no_reports = dataclasses.replace(deps, reports=lambda lk: [])

        def local_fn(variant):
            def run(question):
                started = time.monotonic()
                answer, context = answer_local(variant, llm, question)
                cited = [c for c in answer.check.cited if c.startswith("T")]
                passages = {}
                if context:
                    shown = context.by_label()
                    passages = {c: shown[c].text for c in cited if c in shown}
                return AnswerRecord(
                    "local", answer.text, answer.status, answer.cost_usd,
                    round(time.monotonic() - started, 2), answer.check.status,
                    answer.check.cited, passages,
                )  # fmt: skip

            return run

        def baseline_fn(question):
            started = time.monotonic()
            try:
                result = answer_question(question, qdrant, engine, embedder, llm, k=6)
            except AnswerError as error:
                raise LlmError(f"baseline failed: {error}") from error
            return AnswerRecord(
                "baseline", result.answer, "refused" if result.refused else "answered",
                result.cost_usd or 0.0, round(time.monotonic() - started, 2),
            )  # fmt: skip

        fns = {"baseline": baseline_fn, "local_no_reports": local_fn(no_reports),
               "local": local_fn(deps)}  # fmt: skip
        rows, cost, skipped = run_correctness(
            engine, llm, hard, fns, args.max_cost_usd,
            on_progress=lambda d, n, c: print(f"  answers {d}/{n}, ${c:.4f}"),
        )  # fmt: skip
        spent += cost
        summary = summarize(rows)

        support = {"checked": 0, "supported": 0, "answers": 0}
        for row in support_sample(rows, "local", 20):
            if spent >= args.max_cost_usd:
                break
            try:
                checked, supported, price = check_support(engine, llm, row)
            except LlmError:
                continue
            spent += price
            support["checked"] += checked
            support["supported"] += supported
            support["answers"] += 1
        support["precision"] = (
            round(support["supported"] / support["checked"], 3) if support["checked"] else None
        )

        def status_of(question: str) -> str:
            route = route_question(question, index, llm)
            if route.mode == "relate":
                result = answer_relate(
                    driver, llm, index, question, predicates, args.index_version,
                    lambda ids: postgres_unit_rows(engine, ids), lambda s: len(encoder.encode(s)),
                )  # fmt: skip
                return result.status
            if route.mode == "global":
                chosen = select_communities(
                    driver, embedder.dense_query, question, args.index_version
                )
                if not chosen:
                    return "no_report"
                return "answered"
            if route.mode == "baseline":
                try:
                    return "refused" if answer_question(
                        question, qdrant, engine, embedder, llm, k=6
                    ).refused else "answered"  # fmt: skip
                except AnswerError:
                    return "refused"
            return fns["local"](question).status

        statuses = {}
        for q in unanswerable:
            if spent >= args.max_cost_usd:
                break
            statuses[q["id"]] = status_of(q["question"])
        refusal = refusal_accuracy(statuses)

        relate = {"pairs": 0, "path_found": 0, "right_length": 0, "answered": 0, "verified": 0}
        for q in pairs:
            if spent >= args.max_cost_usd:
                break
            result = answer_relate(
                driver, llm, index, q["question"], predicates, args.index_version,
                lambda ids: postgres_unit_rows(engine, ids), lambda s: len(encoder.encode(s)),
            )  # fmt: skip
            spent += result.cost_usd
            relate["pairs"] += 1
            relate["path_found"] += bool(result.paths)
            relate["right_length"] += (
                bool(result.paths) and result.paths[0].length == q["expected_hops"]
            )
            relate["answered"] += result.status == "answered"
            relate["verified"] += result.check.status == "verified"

    label = args.label or date.today().isoformat()
    report = {
        "correctness": summary,
        "local_vs_baseline": paired(rows, "local", "baseline"),
        "local_vs_no_reports": paired(rows, "local", "local_no_reports"),
        "support": support, "refusal": refusal, "relate": relate,
        "skipped_by_cap": skipped, "cost_usd": round(spent, 4),
        "answers": [
            {"id": r.question_id, "system": r.system, "status": r.record.status,
             "verdict": r.verdict, "reason": r.reason, "text": r.record.text,
             "check": r.record.check_status, "failed": r.failed}
            for r in rows
        ],
    }  # fmt: skip
    (args.out_dir / f"local-eval-{label}.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    for system, s in summary.items():
        print(f"{system}: {s['correct']} correct, {s['partial']} partial, {s['incorrect']} "
              f"incorrect of {s['questions']} (share correct {s['share_correct']}, "
              f"interval {s['ci95']}), mean {s['mean_seconds']} s")  # fmt: skip
    print("local vs baseline:", report["local_vs_baseline"])
    print("citation support:", support)
    print("refusal:", refusal)
    print("relate:", relate)
    print(f"cost ${spent:.4f}")
    return 0


def _route_eval(args) -> int:
    import json

    from neo4j import GraphDatabase

    from graphlens_pipeline.linking import EntityIndex
    from graphlens_pipeline.router import route_question

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        index = EntityIndex.from_neo4j(driver, args.index_version)
    questions = [
        q
        for path in args.questions
        for q in json.loads(path.read_text(encoding="utf-8"))["questions"]
    ]

    def acceptable(q: dict) -> set[str]:
        """A one-fact question about a named paper may go to baseline or local; a multi-hop
        one to local; a corpus-wide one to global; a pair question to relate."""
        if q.get("expected_modes"):
            return set(q["expected_modes"])
        if q["kind"] == "global":
            return {"global"}
        if q["kind"] == "relate":
            return {"relate"}
        return {"baseline", "local"} if q.get("hops", 1) <= 1 else {"local"}

    right = 0
    by_kind: dict[str, list[int]] = {}
    for q in questions:
        route = route_question(q["question"], index)
        ok = route.mode in acceptable(q)
        right += ok
        by_kind.setdefault(q["kind"], []).append(int(ok))
        if args.show_misses and not ok:
            print(f"  MISS {q['id']}: routed {route.mode} ({route.confidence:.2f}), "
                  f"expected {sorted(acceptable(q))}: {q['question'][:90]}")  # fmt: skip
    share = right / len(questions)
    print(f"router (rules only): {right} of {len(questions)} acceptable ({share:.0%})")
    for kind, results in sorted(by_kind.items()):
        print(f"  {kind}: {sum(results)} of {len(results)}")
    return 0


def _ask_auto(engine, args) -> int:
    """Route the question, then run the chosen mode through the same commands as before."""
    from neo4j import GraphDatabase

    from graphlens_pipeline.linking import EntityIndex
    from graphlens_pipeline.llm import LlmError, OpenAiLlm
    from graphlens_pipeline.router import route_question

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    llm = None
    if not args.route_only:
        try:
            llm = OpenAiLlm(model=os.environ.get("LLM_MODEL_SMALL") or None)
        except LlmError as error:
            print(f"Cannot start: {error}", file=sys.stderr)
            return 2
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        index = EntityIndex.from_neo4j(driver, args.index_version)
    route = route_question(args.question, index, llm, args.mode)
    note = " (low confidence)" if route.ran_as_fallback else ""
    print(
        f"mode: {route.mode}{note} | chosen by {route.source}, confidence {route.confidence:.2f}"
        f" | {route.reason}"
    )
    if route.ran_as_fallback:
        print("  The question was unclear, so it ran as local. Force a mode with --mode.")
    if args.route_only:
        return 0
    args.show_context = False
    args.paths_only = False
    if route.mode == "local":
        return _local_ask(engine, args)
    if route.mode == "relate":
        return _relate(engine, args)
    if route.mode == "global":
        args.level, args.max_reports, args.threshold = 1, 40, None
        args.no_dynamic, args.select_only = False, False
        return _global_ask(args)
    return _ask(engine, args.question, 6)


def _relate(engine, args) -> int:
    import tiktoken
    from neo4j import GraphDatabase

    from graphlens_pipeline.linking import EmptyQuestion, EntityIndex
    from graphlens_pipeline.llm import LlmError, OpenAiLlm
    from graphlens_pipeline.localcontext import postgres_unit_rows
    from graphlens_pipeline.ontology import load_ontology
    from graphlens_pipeline.relate import answer_relate, find_paths, link_pair, shared_communities

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    predicates = load_ontology(args.ontology).predicate_names
    encoder = tiktoken.get_encoding("o200k_base")
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        index = EntityIndex.from_neo4j(driver, args.index_version)
        try:
            if args.paths_only:
                ends, early = link_pair(index, args.question)
                if early:
                    print(f"{early.status}: {early.reason} {'; '.join(early.options)}")
                    return 0
                paths = find_paths(driver, ends[0].id, ends[1].id, predicates, args.index_version)
                print(f"{ends[0].name}  <->  {ends[1].name}: {len(paths)} path(s)")
                for path in paths:
                    names = " | ".join(f"{h.predicate}" for h in path.hops)
                    print("  " + " - ".join(n["name"] for n in path.nodes) + f"   [{names}]")
                if not paths:
                    for c in shared_communities(driver, ends[0].id, ends[1].id, args.index_version):
                        print(f"  shared community (level {c['level']}): {c['title']}")
                return 0
            llm = OpenAiLlm(model=os.environ.get("LLM_MODEL_SMALL") or None)
            answer = answer_relate(
                driver, llm, index, args.question, predicates, args.index_version,
                lambda ids: postgres_unit_rows(engine, ids), lambda s: len(encoder.encode(s)),
            )  # fmt: skip
        except (EmptyQuestion, LlmError) as error:
            print(f"Cannot answer: {error}")
            return 1
    print(f"mode: relate | status: {answer.status} | {' <-> '.join(answer.ends)}")
    for path in answer.paths:
        print("  " + " - ".join(n["name"] for n in path.nodes))
    if answer.text:
        print(chr(10) + answer.text + chr(10))
        print(f"citation check: {answer.check.status}; cited {answer.check.cited}")
        if answer.check.unknown_labels:
            print(f"  labels not in the context: {answer.check.unknown_labels}")
        for sentence in answer.check.unsupported:
            print(f"  names an entity the context never mentions: {sentence}")
    else:
        print(answer.reason, "; ".join(answer.options))
        for c in answer.shared_communities:
            print(f"  shared community (level {c['level']}, {c['size']} entities): {c['title']}")
        print(answer.suggestion)
    print(f"cost ${answer.cost_usd:.5f}")
    return 0


def _export_replay(engine, args) -> int:
    """Free: rebuild passages and graphs for saved answers; keep only entries that still match."""
    import json

    from neo4j import GraphDatabase

    from graphlens_pipeline.replayexport import (
        baseline_entry,
        build_local_entry,
        build_refusal_entry,
    )

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password and os.environ.get("QDRANT_URL")):
        print("NEO4J_* and QDRANT_URL must be set.", file=sys.stderr)
        return 2
    saved = json.loads(args.eval_json.read_text(encoding="utf-8"))["answers"]
    by_system = {(a["id"], a["system"]): a for a in saved}
    questions = {
        q["id"]: q["question"]
        for q in json.loads(args.questions.read_text(encoding="utf-8"))["questions"]
    }
    refusals = {
        q["id"]: q["question"]
        for q in json.loads(args.unanswerable.read_text(encoding="utf-8"))["questions"]
    }
    entries, skipped = [], []
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        deps = _local_deps(engine, driver, args)
        for qid, question in questions.items():
            if len(entries) >= args.count:
                break
            local = by_system.get((qid, "local"))
            base = by_system.get((qid, "baseline"))
            if not (local and base and local["status"] == "answered"):
                continue
            if local["verdict"] != "correct" or local["check"] != "verified":
                continue
            entry, why = build_local_entry(deps, deps.index, question, local)
            if entry is None:
                skipped.append((qid, why))
                continue
            entries.append(
                {"id": qid, "question": question, "answer": entry, "baseline": baseline_entry(base)}
            )
        for qid in args.refuse:
            entry, why = build_refusal_entry(deps, refusals[qid])
            if entry is None:
                skipped.append((qid, why))
                continue
            entries.append({"id": qid, "question": refusals[qid], "answer": entry})
    args.out.write_text(json.dumps({"entries": entries}, indent=1, ensure_ascii=False), "utf-8")
    print(f"wrote {len(entries)} entries to {args.out}")
    for qid, why in skipped:
        print(f"  skipped {qid}: {why}")
    return 0


def _local_ask(engine, args) -> int:
    from neo4j import GraphDatabase

    from graphlens_pipeline.linking import EmptyQuestion
    from graphlens_pipeline.llm import LlmError, OpenAiLlm
    from graphlens_pipeline.localanswer import answer_local

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password and os.environ.get("QDRANT_URL")):
        print("NEO4J_* and QDRANT_URL must be set.", file=sys.stderr)
        return 2
    try:
        llm = OpenAiLlm(model=os.environ.get("LLM_MODEL_SMALL") or None)
    except LlmError as error:
        print(f"Cannot start: {error}", file=sys.stderr)
        return 2
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        deps = _local_deps(engine, driver, args)
        try:
            answer, context = answer_local(deps, llm, args.question)
        except EmptyQuestion as error:
            print(f"Cannot answer: {error}")
            return 1
    print(f"mode: local | status: {answer.status} | seeds: {', '.join(answer.seeds) or '-'}")
    if answer.status == "answered":
        print(chr(10) + answer.text + chr(10))
        check = answer.check
        print(f"citation check: {check.status}; cited {check.cited}")
        if check.unknown_labels:
            print(f"  labels not in the context: {check.unknown_labels}")
        for sentence in check.unsupported:
            print(f"  names an entity the context never mentions: {sentence}")
    else:
        print(answer.reason)
        if answer.options:
            print("options: " + "; ".join(answer.options))
        print(answer.suggestion)
    print(f"cost ${answer.cost_usd:.5f}, {answer.tokens_in} tokens in, {answer.seconds} s")
    if args.show_context and context:
        print(context.prompt)
    return 0


def _local_context(engine, args) -> int:
    import tiktoken
    from neo4j import GraphDatabase
    from qdrant_client import QdrantClient

    from graphlens_pipeline.embed import LIVE_ALIAS, FastEmbedder
    from graphlens_pipeline.linking import EntityIndex, link_question
    from graphlens_pipeline.localcontext import (
        assemble,
        candidate_units,
        postgres_unit_rows,
        qdrant_unit_vectors,
        seed_reports,
        similarity_to_question,
    )
    from graphlens_pipeline.localgraph import build_subgraph
    from graphlens_pipeline.ontology import load_ontology

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    qdrant_url = os.environ.get("QDRANT_URL")
    if not (uri and user and password and qdrant_url):
        print("NEO4J_* and QDRANT_URL must be set.", file=sys.stderr)
        return 2
    encoder = tiktoken.get_encoding("o200k_base")
    embedder = FastEmbedder()
    predicates = load_ontology(args.ontology).predicate_names
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        index = EntityIndex.from_neo4j(driver, args.index_version)
        link = link_question(driver, embedder.dense_query, index, args.question, args.index_version)
        if not link.confident:
            print(f"Not enough to go on (best vector score {link.best_vector_score:.3f}).")
            return 0
        vector = embedder.dense_query(link.question)
        graph = build_subgraph(driver, link.seeds, vector, predicates, args.index_version)
        reports = seed_reports(driver, link.seeds, args.index_version)
    cited = candidate_units(graph)
    similarity = similarity_to_question(
        vector, qdrant_unit_vectors(QdrantClient(url=qdrant_url), list(cited), LIVE_ALIAS)
    )
    rows = postgres_unit_rows(engine, list(cited))
    context = assemble(
        link.question, graph, rows, similarity, reports, lambda s: len(encoder.encode(s))
    )
    print("seeds:", ", ".join(f"{s.name} ({s.source}, w={s.weight})" for s in link.seeds))
    print(f"subgraph: {len(graph.nodes)} nodes, {len(graph.edges)} edges, {graph.candidates} found")
    print(f"context tokens: {context.tokens} (total {context.total_tokens} of 8000)")
    print(f"left out: {context.left_out}; items: {len(context.items)}")
    if args.show:
        print(context.prompt)
    return 0


def _link_entities(args) -> int:
    import json

    from neo4j import GraphDatabase

    from graphlens_pipeline.embed import FastEmbedder
    from graphlens_pipeline.linking import EmptyQuestion, EntityIndex, link_question

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    questions = list(args.question)
    if args.file:
        document = json.loads(args.file.read_text(encoding="utf-8"))
        questions += [f"{q['id']}|{q['question']}" for q in document["questions"]]
    if not questions:
        print("Give a question or --file.", file=sys.stderr)
        return 2
    embedder = FastEmbedder()
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        index = EntityIndex.from_neo4j(driver, args.index_version)
        for item in questions:
            label, _, text = item.partition("|") if "|" in item and args.file else ("", "", item)
            try:
                result = link_question(
                    driver, embedder.dense_query, index, text, args.index_version,
                    args.min_vector_score,
                )  # fmt: skip
            except EmptyQuestion as error:
                print(f"{label}: {error}")
                continue
            names = ", ".join(
                f"{s.name} ({s.type}, {s.source}{' AMBIGUOUS' if s.ambiguous else ''}"
                f"{'' if s.source == 'name' else f' {s.score:.3f}'})"
                for s in result.seeds
            )
            print(f"{label} best vector {result.best_vector_score:.3f} | {names or 'no seeds'}")
    return 0


def _global_bench(args) -> int:
    import json
    import statistics

    import tiktoken
    from neo4j import GraphDatabase

    from graphlens_pipeline.embed import FastEmbedder
    from graphlens_pipeline.globalsearch import answer_from_selection, select_communities
    from graphlens_pipeline.llm import LlmError, OpenAiLlm

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    asked = [
        q["question"]
        for q in json.loads(args.questions.read_text(encoding="utf-8"))["questions"]
        if q["kind"] == "global"
    ][: args.n]
    encoder = tiktoken.get_encoding("o200k_base")

    def count(s: str) -> int:
        return len(encoder.encode(s))

    embedder = FastEmbedder()
    dynamic = not args.no_dynamic
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        picks = [
            select_communities(driver, embedder.dense_query, q, args.index_version, dynamic=dynamic)
            for q in asked
        ]
    if args.dry_run:
        tokens = sum(count(i.summary) + count(i.title) + 120 for p in picks for i in p)
        batches = sum(len(p) for p in picks)
        estimate = (tokens * 0.40 + batches * 12 * 1.60) / 1e6 + len(asked) * 0.003
        print(json.dumps({"queries": len(asked), "dynamic": dynamic, "reports_read": batches,
                          "cost_usd_estimate": round(estimate, 3)}))  # fmt: skip
        print("Nothing was spent.")
        return 0
    try:
        llm = OpenAiLlm(model=os.environ.get("LLM_MODEL_SMALL") or None)
    except LlmError as error:
        print(f"Cannot start: {error}", file=sys.stderr)
        return 2
    seconds, costs, partial, spent = [], [], 0, 0.0
    for question, selected in zip(asked, picks, strict=True):
        if spent >= args.max_cost_usd:
            print("cost cap reached, stopping")
            break
        answer = answer_from_selection(llm, question, selected, count, dynamic=dynamic)
        seconds.append(answer.seconds)
        costs.append(answer.cost_usd)
        partial += answer.partial
        spent += answer.cost_usd
        print(f"  {answer.seconds:6.1f} s  ${answer.cost_usd:.4f}  partial={answer.partial}")
    ordered = sorted(seconds)
    p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))] if ordered else 0
    print(json.dumps({
        "queries": len(seconds), "dynamic": dynamic, "partial_answers": partial,
        "seconds_median": round(statistics.median(seconds), 1) if seconds else None,
        "seconds_p95_of_this_sample": round(p95, 1), "seconds_max": max(seconds, default=None),
        "cost_usd_mean": round(statistics.mean(costs), 4) if costs else None,
        "cost_usd_max": max(costs, default=None), "cost_usd_total": round(spent, 4),
    }, indent=2))  # fmt: skip
    return 0


def _review_sheets(args) -> int:
    import json

    from neo4j import GraphDatabase

    from graphlens_pipeline.reports import read_graph_data
    from graphlens_pipeline.reviewsheets import (
        render_community_sheet,
        render_verdict_sheet,
        sample_communities,
        sample_verdicts,
    )

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        graph = read_graph_data(driver, args.index_version)
        with driver.session() as session:
            rows = [
                dict(r)
                for r in session.run(
                    "MATCH (c:Community {index_version: $v}) WHERE c.report_title IS NOT NULL"
                    " OPTIONAL MATCH (e:Entity)-[:IN_COMMUNITY]->(c)"
                    " RETURN c.id AS id, c.level AS level, c.size AS size, c.is_stub AS is_stub,"
                    " c.report_title AS title, c.report_summary AS summary,"
                    " c.report_findings AS findings, collect(e.id) AS member_ids",
                    v=args.index_version,
                )
            ]  # fmt: skip
    degree: dict[str, int] = {}
    for relation in graph.relations:
        for end in (relation["a"], relation["b"]):
            degree[end] = degree.get(end, 0) + 1
    for row in rows:
        ranked = sorted(
            row["member_ids"], key=lambda m: (-degree.get(m, 0), graph.entities[m]["name"])
        )
        row["members"] = [
            f"{graph.entities[m]['name']} ({graph.entities[m]['type']})" for m in ranked[:12]
        ]
    communities = sample_communities(rows)
    results = json.loads(args.results.read_text(encoding="utf-8"))["dynamic"]["results"]
    verdicts = sample_verdicts(results)
    (args.out_dir / "REVIEW_COMMUNITIES.md").write_text(
        render_community_sheet(communities), encoding="utf-8"
    )
    (args.out_dir / "REVIEW_VERDICTS.md").write_text(
        render_verdict_sheet(verdicts), encoding="utf-8"
    )
    print(f"{len(communities)} communities and {len(verdicts)} judged questions written")
    return 0


def _global_eval(engine, args) -> int:
    import json
    import threading
    from datetime import date

    import tiktoken
    from neo4j import GraphDatabase
    from qdrant_client import QdrantClient

    from graphlens_pipeline.answer import AnswerError, answer_question
    from graphlens_pipeline.embed import FastEmbedder
    from graphlens_pipeline.globaleval import (
        _key,
        cached,
        render_report,
        run_global_eval,
        store,
        win_rates,
    )
    from graphlens_pipeline.globalsearch import answer_from_selection, select_communities
    from graphlens_pipeline.llm import LlmError, OpenAiLlm

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    qdrant_url = os.environ.get("QDRANT_URL")
    if not (uri and user and password and qdrant_url):
        print("NEO4J_* and QDRANT_URL must be set.", file=sys.stderr)
        return 2
    questions = [
        q
        for path in args.questions
        for q in json.loads(path.read_text(encoding="utf-8"))["questions"]
        if q["kind"] == "global"
    ]
    encoder = tiktoken.get_encoding("o200k_base")

    def count(s: str) -> int:
        return len(encoder.encode(s))

    embedder, embed_lock = FastEmbedder(), threading.Lock()
    driver = GraphDatabase.driver(uri, auth=(user, password))

    def query_vector(question: str):
        with embed_lock:
            return embedder.dense_query(question)

    if args.dry_run:
        per = {"baseline": 0.0012, "ours": 0.008, "judge_call": 0.0015}
        fresh_base = fresh_ours = 0
        for q in questions:
            if cached(engine, _key("baseline", q["question"])) is None:
                fresh_base += 1
            sel = select_communities(driver, query_vector, q["question"], args.index_version)
            signature = ",".join(s.id for s in sel)
            if cached(engine, _key("ours", q["question"], "dynamic", signature)) is None:
                fresh_ours += 1
        full = select_communities(
            driver, query_vector, questions[0]["question"], args.index_version, dynamic=False
        )
        tokens = sum(count(s.summary) + count(s.title) + 120 for s in full)
        ablation = min(args.ablation_questions, len(questions))
        full_cost = (tokens * 0.40 + (tokens // 6000 + 1) * 700 * 1.60) / 1e6 + 0.003
        comparisons = len(questions) + ablation
        total = (
            fresh_base * per["baseline"]
            + fresh_ours * per["ours"]
            + ablation * full_cost
            + comparisons * 2 * per["judge_call"]
        )
        print(
            json.dumps(
                {
                    "global_questions": len(questions),
                    "fresh_baseline_answers": fresh_base,
                    "fresh_global_answers": fresh_ours,
                    "ablation_questions": ablation,
                    "reports_without_selection": len(full),
                    "map_tokens_without_selection": tokens,
                    "judge_calls": comparisons * 2,
                    "cost_usd_estimate": round(total, 3),
                    "cost_usd_with_margin": round(total * 1.4, 3),
                },
                indent=2,
            )
        )
        print("Per-call prices are assumptions checked on one real question. Nothing was spent.")
        driver.close()
        return 0

    try:
        llm = OpenAiLlm(model=os.environ.get("LLM_MODEL_SMALL") or None)
    except LlmError as error:
        print(f"Cannot start: {error}", file=sys.stderr)
        return 2
    qdrant = QdrantClient(url=qdrant_url)

    def baseline_for(question: str):
        key = _key("baseline", question)
        hit = cached(engine, key)
        if hit:
            return hit["text"], 0.0
        try:
            with embed_lock:
                result = answer_question(question, qdrant, engine, embedder, llm, k=6)
        except AnswerError as error:
            raise LlmError(f"baseline failed: {error}") from error
        store(engine, key, {"text": result.answer})
        return result.answer, result.cost_usd or 0.0

    def ours_with(dynamic: bool):
        def ours_for(question: str):
            sel = select_communities(
                driver, query_vector, question, args.index_version, dynamic=dynamic
            )
            mode = "dynamic" if dynamic else "all"
            key = _key("ours", question, mode, ",".join(s.id for s in sel))
            hit = cached(engine, key)
            if hit:
                return hit["text"], hit["partial"], 0.0
            answer = answer_from_selection(llm, question, sel, count, dynamic=dynamic)
            if not answer.partial:  # a partial answer is not kept, so a rerun can complete it
                store(engine, key, {"text": answer.text, "partial": answer.partial})
            return answer.text, answer.partial, answer.cost_usd

        return ours_for

    def progress(done: int, total: int, cost: float) -> None:
        print(f"  {done}/{total} questions, ${cost:.4f}")

    label = args.label or date.today().isoformat()
    main = run_global_eval(
        engine, llm, questions, baseline_for, ours_with(True), args.max_cost_usd,
        on_progress=progress,
    )  # fmt: skip
    remaining = max(args.max_cost_usd - main.cost_usd, 0.0)
    ablation = run_global_eval(
        engine, llm, questions[: args.ablation_questions], baseline_for, ours_with(False),
        remaining, on_progress=progress,
    )  # fmt: skip
    driver.close()
    rates, rates_all = win_rates(main.results), win_rates(ablation.results)
    from sqlalchemy import text as sql_text

    from graphlens_pipeline.quality import Check, save_checks

    with engine.connect() as conn:
        report_run = conn.execute(
            sql_text("SELECT id FROM index_runs WHERE index_version = :v"),
            {"v": f"{args.index_version}-reports"},
        ).first()
    if report_run:
        targets = {
            "comprehensiveness": 0.60,
            "diversity": 0.60,
            "empowerment": 0.5,
            "directness": 0.5,
        }
        save_checks(
            engine,
            str(report_run[0]),
            [
                Check(
                    f"global_win_rate_{name}", r["win_rate"], targets[name], True,
                    {**r, "blueprint_target": name in ("comprehensiveness", "diversity"),
                     "judge": llm.model, "order_swapped": True},
                )
                for name, r in rates.items()
                if r["win_rate"] is not None
            ],
        )  # fmt: skip
    note = (
        "Judge and answerer are the same model family and the question set is small; read the "
        "interval, not only the rate."
    )
    report = render_report(f"dynamic selection ({label})", rates, main, note)
    report += "\n" + render_report(
        f"no selection, first {len(ablation.results)} questions ({label})", rates_all, ablation
    )
    (args.out_dir / f"global-{label}.md").write_text(report, encoding="utf-8")

    def dump(run):
        return [
            {
                "id": r.question_id, "question": r.question, "baseline": r.baseline_answer,
                "ours": r.ours_answer, "partial": r.ours_partial, "failed": r.failed,
                "outcome": r.judgement.outcome if r.judgement else None,
                "reasons": r.judgement.reasons if r.judgement else None,
                "cost_usd": r.cost_usd,
            }
            for r in run.results
        ]  # fmt: skip

    payload = {
        "dynamic": {"rates": rates, "cost_usd": main.cost_usd, "results": dump(main)},
        "no_selection": {
            "rates": rates_all,
            "cost_usd": ablation.cost_usd,
            "results": dump(ablation),
        },
    }
    (args.out_dir / f"global-{label}.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    for name, r in rates.items():
        rate = "-" if r["win_rate"] is None else f"{r['win_rate']:.0%}"
        print(
            f"{name}: {rate} ({r['wins']} wins, {r['ties']} ties, {r['losses']} losses of {r['n']})"
        )
    print(f"cost ${main.cost_usd + ablation.cost_usd:.4f}")
    return 0


def _global_ask(args) -> int:
    import json

    import tiktoken
    from neo4j import GraphDatabase

    from graphlens_pipeline.embed import FastEmbedder
    from graphlens_pipeline.globalsearch import (
        THRESHOLD,
        answer_from_selection,
        select_communities,
    )
    from graphlens_pipeline.llm import LlmError, OpenAiLlm

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    threshold = THRESHOLD if args.threshold is None else args.threshold
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        selected = select_communities(
            driver, FastEmbedder().dense_query, args.question, args.index_version,
            args.level, args.max_reports, threshold, dynamic=not args.no_dynamic,
        )  # fmt: skip
    print(f"selected {len(selected)} reports at level {args.level} (threshold {threshold})")
    if args.select_only:
        for item in selected[:15]:
            print(f"  {item.score:.3f}  {item.label}  {item.title[:90]}")
        return 0
    try:
        llm = OpenAiLlm(model=os.environ.get("LLM_MODEL_SMALL") or None)
    except LlmError as error:
        print(f"Cannot start: {error}", file=sys.stderr)
        return 2
    encoder = tiktoken.get_encoding("o200k_base")
    answer = answer_from_selection(
        llm, args.question, selected, lambda s: len(encoder.encode(s)),
        on_progress=lambda done, total, state: print(f"  map batch {done}/{total}: {state}"),
        dynamic=not args.no_dynamic,
    )  # fmt: skip
    print(chr(10) + answer.text + chr(10))
    print(json.dumps({
        "partial": answer.partial, "batches": answer.batches,
        "failed_batches": answer.failed_batches,
        "reports_selected": answer.selected, "reports_used": len(answer.used),
        "cost_usd": answer.cost_usd, "seconds": answer.seconds,
    }))  # fmt: skip
    for item in answer.used:
        print(f"  [{item.label}] {item.title}")
    return 0


def _community_embed(args) -> int:
    import json

    from neo4j import GraphDatabase

    from graphlens_pipeline.embed import FastEmbedder
    from graphlens_pipeline.graphstore import apply_schema
    from graphlens_pipeline.reports import embed_reports

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        apply_schema(driver)
        print(json.dumps(embed_reports(driver, FastEmbedder().dense, args.index_version)))
    return 0


def _community_quality(engine, args) -> int:
    from neo4j import GraphDatabase
    from sqlalchemy import text

    from graphlens_pipeline.quality import (
        community_checks,
        read_community_state,
        save_checks,
    )

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    with engine.connect() as conn:
        run = conn.execute(
            text("SELECT id FROM index_runs WHERE index_version = :v"), {"v": args.run_version}
        ).first()
    if not run:
        print(
            f"No run record for {args.run_version}; run community-reports first.", file=sys.stderr
        )
        return 1
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        entities, communities = read_community_state(driver, args.index_version)
    if not communities:
        print("No communities; run the communities command first.", file=sys.stderr)
        return 1
    checks = community_checks(entities, communities, engine)
    save_checks(engine, str(run[0]), checks)
    for check in checks:
        print(f"{'PASS' if check.passed else 'MISS'}  {check.name}: {check.value:.1%}")
    return 0 if all(c.passed for c in checks) else 1


def _labels(engine, args) -> int:
    from sqlalchemy import text

    from graphlens_pipeline import labelsets as ls
    from graphlens_pipeline.extract import load_cached_results, load_units
    from graphlens_pipeline.ontology import load_ontology
    from graphlens_pipeline.quality import Check, save_checks

    relations_file, pairs_file = args.dir / "relations_v0.json", args.dir / "pairs_v0.json"
    with engine.connect() as conn:
        run = conn.execute(
            text("SELECT id FROM index_runs WHERE index_version = :v"), {"v": args.index_version}
        ).first()
    if not run:
        print(f"No run record for {args.index_version}.", file=sys.stderr)
        return 1

    if args.command == "labels-draw":
        if relations_file.exists() or pairs_file.exists():
            print("Label files already exist; not overwriting them.", file=sys.stderr)
            return 1
        model = os.environ.get("LLM_MODEL_SMALL") or "gpt-4.1-mini"
        ontology = load_ontology(args.ontology)
        units = load_units(engine, args.corpus_name)
        results = load_cached_results(engine, units, model, ontology, args.gleaning)
        chosen = ls.draw_units(units, results)
        ls.write_json(relations_file, ls.relation_items(chosen, results))
        ls.write_json(pairs_file, ls.pair_items(engine, str(run[0]), results))
        args.command = "labels-render"

    relations, pairs = ls.read_json(relations_file), ls.read_json(pairs_file)
    problems = ls.validate(relations, pairs)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1

    if args.command == "labels-render":
        (args.dir / "RELATIONS_REVIEW.md").write_text(
            ls.render_relation_review(relations), encoding="utf-8"
        )
        (args.dir / "PAIRS_REVIEW.md").write_text(ls.render_pair_review(pairs), encoding="utf-8")
        n_rel = sum(len(u["relations"]) for u in relations["units"])
        print(
            f"{len(relations['units'])} units with {n_rel} relations, {len(pairs['pairs'])} pairs"
        )
        return 0

    # labels-score
    if args.refresh_decisions:
        changed = ls.refresh_decisions(engine, str(run[0]), pairs)
        ls.write_json(pairs_file, pairs)
        print(f"{changed} labeled pairs now have a different resolver decision")
    precision = ls.relation_precision(relations)
    er = ls.er_scores(pairs)
    checks = []
    for name, score, target in (
        ("relation_precision", precision, 0.80),
        ("entity_resolution_f1", er["f1"], 0.85),
    ):
        if score.value is None:
            print(f"{name}: no labels yet")
            continue
        checks.append(Check(name, score.value, target, True, {
            "counted": score.counted, "unsure": score.unsure,
            "owner_reviewed": score.owner_reviewed, "draft_only": score.draft_only,
            "unlabeled": score.unlabeled, **score.details,
            "precision": er["precision"].value if name.startswith("entity") else None,
            "recall": er["recall"].value if name.startswith("entity") else None,
        }))  # fmt: skip
        reviewed = f"owner-reviewed {score.owner_reviewed}, draft-only {score.draft_only}"
        print(f"{name}: {score.value:.3f} (target {target}; {reviewed}; unsure {score.unsure})")
    if checks:
        save_checks(engine, str(run[0]), checks)
    return 0


def _quality_report(engine, args) -> int:
    from neo4j import GraphDatabase
    from sqlalchemy import text

    from graphlens_pipeline.ontology import load_ontology
    from graphlens_pipeline.quality import (
        Check,
        compute_checks,
        read_graph,
        render_report,
        save_checks,
    )

    uri, user, password = (os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"))
    if not (uri and user and password):
        print("NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD must be set.", file=sys.stderr)
        return 2
    with engine.connect() as conn:
        run = conn.execute(
            text("SELECT id, stats FROM index_runs WHERE index_version = :v"),
            {"v": args.index_version},
        ).first()
    if not run:
        print(f"No run record for {args.index_version}.", file=sys.stderr)
        return 1
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        entities, edges = read_graph(driver, args.index_version)
    if not entities:
        print("The graph is empty; run graph-load first.", file=sys.stderr)
        return 1
    checks = compute_checks(entities, edges, run.stats or {}, load_ontology(args.ontology), engine)
    save_checks(engine, str(run.id), checks)
    shown = list(checks)
    with engine.connect() as conn:  # the rate from before graph-load left lonely entities out
        before = conn.execute(
            text(
                "SELECT value, threshold, details FROM quality_checks"
                " WHERE run_id = :r AND check_name = 'orphan_rate_before_pruning'"
            ),
            {"r": run.id},
        ).first()
    if before:
        shown.append(Check(
            "orphan_rate_before_pruning", float(before[0]), float(before[1]), False, before[2]
        ))  # fmt: skip
    report = render_report(shown, args.index_version)
    if args.out:
        args.out.write_text(report, encoding="utf-8")
    for check in checks:
        print(f"{'PASS' if check.passed else 'MISS'}  {check.name}: {check.value:.1%}")
    return 0


def _resolve(engine, args) -> int:
    import json
    from collections import Counter

    from sqlalchemy import text

    from graphlens_pipeline.resolve import save_decisions

    computed = _compute_resolution(engine, args)
    if isinstance(computed, int):
        return computed
    result, _, _ = computed
    with engine.connect() as conn:
        run = conn.execute(
            text("SELECT id FROM index_runs WHERE index_version = :v"), {"v": args.index_version}
        ).first()
    if run:
        save_decisions(engine, str(run[0]), result.decisions)
    methods = Counter((d.method, d.decision) for d in result.decisions)
    print(json.dumps({
        "mentions": result.mentions, "noise_dropped": result.dropped_noise,
        "groups_after_exact_merge": result.clusters_before_merging_pairs,
        "entities_final": len(result.entities), "relations_final": len(result.relations),
        "aliases_kept": sum(len(e.aliases) for e in result.entities),
        "by_type": dict(Counter(e.type for e in result.entities)),
        "decisions": {f"{m}/{d}": n for (m, d), n in sorted(methods.items())},
        "model_calls": result.model_calls, "model_cost_usd": result.model_cost_usd,
        "pairs_left_unasked": result.unasked_pairs, "decisions_saved": bool(run),
    }, indent=2))  # fmt: skip
    return 0


def _extract_estimate(engine, args) -> int:
    import json

    from graphlens_pipeline.extract import estimate_cost, load_units
    from graphlens_pipeline.ontology import load_ontology

    model = os.environ.get("LLM_MODEL_SMALL") or "gpt-4.1-mini"
    units = load_units(engine, args.corpus_name)
    rows = estimate_cost(units, load_ontology(DEFAULT_ONTOLOGY), model)
    print(json.dumps({"model": model, "estimates": rows}, indent=2))
    print("Prompt tokens are counted exactly; answer sizes are assumptions. Nothing was spent.")
    return 0


def _extract(engine, args) -> int:
    import json

    from graphlens_pipeline.extract import load_units, run_extraction
    from graphlens_pipeline.llm import LlmError, OpenAiLlm
    from graphlens_pipeline.ontology import load_ontology
    from graphlens_pipeline.runs import begin_stage, end_stage, finish_run, start_run

    ontology = load_ontology(args.ontology)
    try:
        llm = OpenAiLlm(model=os.environ.get("LLM_MODEL_SMALL") or None)
    except LlmError as error:
        print(f"Cannot start: {error}", file=sys.stderr)
        return 2
    units = load_units(engine, args.corpus_name, args.sample)
    sample = args.sample < 1
    config = {
        "model": llm.model, "ontology": ontology.fingerprint(), "prompt": "extract-v1",
        "gleaning_passes": args.gleaning, "sample": args.sample, "units": len(units),
    }  # fmt: skip
    run = start_run(engine, args.corpus_name, args.index_version, config, args.max_cost_usd, sample)
    begin_stage(engine, run, "extract", len(units))

    def progress(done: int, total: int, spent: float) -> None:
        if done % 10 == 0 or done == total:
            print(f"  {done}/{total} units, ${spent:.4f} spent", flush=True)

    try:
        report = run_extraction(
            engine, llm, ontology, units, args.gleaning, args.max_cost_usd, args.workers, progress
        )
    except Exception as error:  # record the failure on the run, then stop
        end_stage(engine, run, "extract", 0, 0.0, error=type(error).__name__)
        finish_run(engine, run, "failed", 0.0, 0, 0, {"error": type(error).__name__})
        raise
    done = report.extracted + report.from_cache
    end_stage(engine, run, "extract", done, report.cost_usd)
    capped = report.stopped_by_cap or bool(report.failed)
    finish_run(
        engine, run, "cancelled" if sample and not capped else "running", report.cost_usd,
        report.tokens_in, report.tokens_out,
        {"units": report.units_total, "from_cache": report.from_cache,
         "extracted": report.extracted, "failed": len(report.failed),
         "skipped_by_cap": report.skipped_by_cap,
         "entities": report.entities, "relations": report.relations, "rejected": report.rejected,
         "outcome": "sample_completed" if sample and not capped else "in_progress"},
    )  # fmt: skip
    new = max(1, report.extracted)
    print(json.dumps({
        "model": llm.model, "units": report.units_total, "extracted_now": report.extracted,
        "from_cache": report.from_cache, "failed": report.failed,
        "skipped_by_cost_cap": report.skipped_by_cap, "entities": report.entities,
        "relations": report.relations, "rejected": report.rejected,
        "tokens_in": report.tokens_in, "tokens_out": report.tokens_out,
        "cost_usd": report.cost_usd, "cost_per_new_unit_usd": round(report.cost_usd / new, 6),
    }, indent=2))  # fmt: skip
    return 1 if capped else 0


def _eval_run(engine, args) -> int:
    import datetime as dt
    import json
    from dataclasses import asdict

    from qdrant_client import QdrantClient
    from sqlalchemy import text

    from graphlens_pipeline.embed import FastEmbedder
    from graphlens_pipeline.evalrun import (
        by_kind,
        estimate_cost,
        make_answer_fn,
        render_results,
        run_eval,
        save_run,
        summarize,
    )
    from graphlens_pipeline.evalset import load_questions
    from graphlens_pipeline.llm import LlmError, OpenAiLlm

    qdrant_url = os.environ.get("QDRANT_URL")
    if not qdrant_url:
        print("QDRANT_URL is not set.", file=sys.stderr)
        return 2
    questions = [q for q in load_questions(args.questions) if q.get("review") == "approved"]
    if not questions:
        print("No approved questions.", file=sys.stderr)
        return 1
    client, embedder = QdrantClient(url=qdrant_url), FastEmbedder()

    try:
        llm = OpenAiLlm()
    except LlmError as error:
        if not args.dry_run:
            print(f"Cannot start: {error}", file=sys.stderr)
            return 2
        llm = None

    if args.dry_run:
        model = (llm.model if llm else os.environ.get("LLM_MODEL_MAIN")) or "gpt-4.1-mini"
        print(json.dumps(estimate_cost(questions, client, engine, embedder, model), indent=2))
        print("Dry run: no model was called, nothing was spent.")
        return 0

    outcomes, capped = run_eval(
        questions, make_answer_fn(client, engine, embedder, llm), llm, args.max_cost_usd
    )
    summary, kinds = summarize(outcomes), by_kind(outcomes)
    git_sha = os.environ.get("GIT_SHA", "unknown")
    with engine.connect() as conn:
        units = conn.execute(text("SELECT count(*) FROM text_units")).scalar_one()
    meta = {"date": dt.date.today().isoformat(), "model": llm.model, "git_sha": git_sha,
            "units": units}  # fmt: skip
    config = {**meta, "passages_per_question": 6, "max_cost_usd": args.max_cost_usd}
    run_id = save_run(engine, questions, outcomes, config, {"all": summary, **kinds}, git_sha)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"baseline-{meta['date']}"
    (args.out_dir / f"{stem}.md").write_text(
        render_results(summary, kinds, outcomes, meta), encoding="utf-8"
    )
    (args.out_dir / f"{stem}.json").write_text(
        json.dumps({"meta": meta, "summary": summary, "by_kind": kinds,
                    "outcomes": [asdict(o) for o in outcomes]}, indent=2) + "\n",
        encoding="utf-8",
    )  # fmt: skip
    print(f"Run {run_id}: {summary['questions_run']}/{summary['questions_total']} questions, "
          f"cost ${summary['total_cost_usd']}, correct {summary['correct']}")  # fmt: skip
    if capped:
        print("STOPPED: the cost cap was reached before all questions ran.", file=sys.stderr)
        return 1
    return 0


def _ask(engine, question: str, k: int) -> int:
    qdrant_url = os.environ.get("QDRANT_URL")
    if not qdrant_url:
        print("QDRANT_URL is not set.", file=sys.stderr)
        return 2
    from qdrant_client import QdrantClient

    from graphlens_pipeline.answer import AnswerError, answer_question
    from graphlens_pipeline.embed import FastEmbedder
    from graphlens_pipeline.llm import LlmError, OpenAiLlm

    try:
        result = answer_question(
            question, QdrantClient(url=qdrant_url), engine, FastEmbedder(), OpenAiLlm(), k=k
        )
    except (AnswerError, LlmError) as error:
        print(f"Could not answer: {error}", file=sys.stderr)
        return 1

    print(f"\nQ: {result.question}\n\nA: {result.answer}\n")
    for passage in result.passages:
        mark = "*" if passage.number in result.cited else " "
        label = f"{passage.paper_id} | {passage.section[:32]} | {passage.title[:60]}"
        print(f" {mark}[{passage.number}] {label}")
    if result.refused:
        print("\nRefused: not enough evidence in the retrieved passages.")
    elif result.citations_valid:
        print("\nCitation numbers: all match a passage that was sent (support not checked).")
    else:
        print(
            f"\nWARNING: citations missing or invalid {result.invalid_citations or '(none cited)'}."
        )
    cost = "unknown" if result.cost_usd is None else f"${result.cost_usd:.5f}"
    print(
        f"Model {result.model}: {result.tokens_in} tokens in, {result.tokens_out} out, "
        f"cost {cost}, {result.latency_ms} ms"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
