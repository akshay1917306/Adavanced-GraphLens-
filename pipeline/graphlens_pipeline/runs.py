"""Run records: one `index_runs` row per index version and one `run_stages` row per stage.

These tables (blueprint 4.4) say what a run was configured to do, what it cost and how far each
stage got, so a run can be inspected and resumed. Meanings used here:

- `running`: the run is in progress, or it stopped early and can be started again with the same
  index version (finished stages are cached and are not paid for twice).
- `failed`: a stage raised an error.
- `passed_gate` and `published`: set later, by the quality gate and the publish step.
- `cancelled`: used for **sample runs** (a 5% dry run before the full run). A sample is never
  published; its results are only for measuring cost and quality (decision D23).
"""

import json
from dataclasses import dataclass

from sqlalchemy import Engine, text


@dataclass(frozen=True)
class Run:
    id: str
    corpus_id: str


def start_run(
    engine: Engine,
    corpus_name: str,
    index_version: str,
    config: dict,
    cost_cap_usd: float,
    sample: bool,
) -> Run:
    """Create the run, or restart it if this index version already exists (a resume)."""
    with engine.begin() as conn:
        corpus = conn.execute(
            text("SELECT id FROM corpora WHERE name = :n"), {"n": corpus_name}
        ).first()
        if corpus is None:
            raise ValueError("corpus not found")
        row = conn.execute(
            text(
                "INSERT INTO index_runs (corpus_id, index_version, status, config, dry_run,"
                " cost_cap_usd, started_at)"
                " VALUES (:corpus, :version, 'running', CAST(:config AS jsonb), :sample, :cap,"
                " now())"
                " ON CONFLICT (corpus_id, index_version) DO UPDATE SET status = 'running',"
                " config = EXCLUDED.config, dry_run = EXCLUDED.dry_run,"
                " cost_cap_usd = EXCLUDED.cost_cap_usd, finished_at = NULL"
                " RETURNING id"
            ),
            {
                "corpus": str(corpus[0]), "version": index_version, "config": json.dumps(config),
                "sample": sample, "cap": round(cost_cap_usd, 2),
            },
        ).one()  # fmt: skip
    return Run(id=str(row[0]), corpus_id=str(corpus[0]))


def begin_stage(engine: Engine, run: Run, stage: str, items_total: int) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO run_stages (run_id, stage, status, items_total, items_done,"
                " cost_usd, error, started_at, finished_at)"
                " VALUES (:run, :stage, 'running', :total, 0, 0, NULL, now(), NULL)"
                " ON CONFLICT (run_id, stage) DO UPDATE SET status = 'running',"
                " items_total = EXCLUDED.items_total, error = NULL, started_at = now(),"
                " finished_at = NULL"
            ),
            {"run": run.id, "stage": stage, "total": items_total},
        )


def end_stage(
    engine: Engine, run: Run, stage: str, items_done: int, cost_usd: float, error: str | None = None
) -> None:
    status = "failed" if error else "done"
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE run_stages SET status = :status, items_done = :done, cost_usd = :cost,"
                " error = :error, finished_at = now() WHERE run_id = :run AND stage = :stage"
            ),
            {"status": status, "done": items_done, "cost": round(cost_usd, 4), "error": error,
             "run": run.id, "stage": stage},
        )  # fmt: skip


def finish_run(
    engine: Engine, run: Run, status: str, cost_usd: float, tokens_in: int, tokens_out: int,
    stats: dict,
) -> None:  # fmt: skip
    if status not in {"running", "failed", "passed_gate", "cancelled"}:
        raise ValueError(f"unexpected run status {status!r}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE index_runs SET status = :status, cost_usd = cost_usd + :cost,"
                " tokens_in = tokens_in + :ti, tokens_out = tokens_out + :to,"
                " stats = CAST(:stats AS jsonb), finished_at = now() WHERE id = :run"
            ),
            {"status": status, "cost": round(cost_usd, 4), "ti": tokens_in, "to": tokens_out,
             "stats": json.dumps(stats), "run": run.id},
        )  # fmt: skip
