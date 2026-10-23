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
    review = sub.add_parser("eval-review", help="write the review page for the owner")
    review.add_argument("--questions", type=Path, default=eval_dir / "questions.json")
    review.add_argument("--out", type=Path, default=Path("/tmp/REVIEW.md"))  # noqa: S108
    index = sub.add_parser("index", help="run the whole flow: ingest, then embed (no OpenAI cost)")
    index.add_argument("--manifest", type=Path, default=Path("/data/corpus/qa_v0/manifest.csv"))
    index.add_argument("--pdf-dir", type=Path, default=Path("/data/corpus/qa_v0/pdfs"))
    index.add_argument("--corpus-name", default=DEFAULT_CORPUS)
    index.add_argument("--corpus-slug", default="qa_v0")
    index.add_argument("--index-version", default="baseline-1")
    load = sub.add_parser("eval-load", help="store the approved questions in the database")
    load.add_argument("--questions", type=Path, default=eval_dir / "questions.json")
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

    if args.command == "eval-load":
        from graphlens_pipeline.evalrun import load_eval_sets
        from graphlens_pipeline.evalset import load_questions

        for name, count in load_eval_sets(engine, load_questions(args.questions)).items():
            print(f"{name}: {'already present' if count == 0 else f'{count} questions loaded'}")
        return 0

    if args.command == "eval-run":
        return _eval_run(engine, args)

    if args.command == "eval-verify":
        from graphlens_pipeline.evalset import fetch_unit_texts, load_questions, verify

        questions = load_questions(args.questions)
        wanted = {item["unit_id"] for q in questions for item in q["evidence"]}
        problems = verify(questions, fetch_unit_texts(engine, wanted), {"local": 30, "global": 10})
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
