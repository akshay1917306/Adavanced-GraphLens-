import pytest
from sqlalchemy import text

from graphlens_pipeline.extract import estimate_cost
from graphlens_pipeline.runs import begin_stage, end_stage, finish_run, start_run
from tests.test_embed import prepare
from tests.test_extract import ONTOLOGY

pytestmark = pytest.mark.integration


def one(engine, sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).one()


def test_a_run_and_its_stage_are_recorded(engine, tmp_path):
    prepare(engine, tmp_path)
    run = start_run(engine, "embed corpus", "idx-test-1", {"model": "m"}, 0.25, sample=True)
    begin_stage(engine, run, "extract", 12)
    end_stage(engine, run, "extract", 12, 0.0412)
    finish_run(engine, run, "cancelled", 0.0412, 9000, 3000, {"outcome": "sample_completed"})

    row = one(
        engine,
        "SELECT status, dry_run, cost_usd, cost_cap_usd, tokens_in, stats->>'outcome' AS o"
        " FROM index_runs WHERE id = :id",
        id=run.id,
    )
    assert (row.status, row.dry_run, float(row.cost_usd), float(row.cost_cap_usd)) == (
        "cancelled",
        True,
        0.0412,
        0.25,
    )
    assert row.tokens_in == 9000 and row.o == "sample_completed"
    stage = one(engine, "SELECT status, items_total, items_done FROM run_stages WHERE run_id = :id",
                id=run.id)  # fmt: skip
    assert tuple(stage) == ("done", 12, 12)


def test_starting_the_same_version_again_resumes_the_same_run(engine, tmp_path):
    prepare(engine, tmp_path)
    first = start_run(engine, "embed corpus", "idx-test-2", {"gleaning": 0}, 1.0, sample=False)
    finish_run(engine, first, "failed", 0.1, 1, 1, {})
    again = start_run(engine, "embed corpus", "idx-test-2", {"gleaning": 2}, 2.0, sample=False)
    assert again.id == first.id
    row = one(engine, "SELECT status, config->>'gleaning' g, cost_usd, finished_at FROM index_runs"
                      " WHERE id = :id", id=first.id)  # fmt: skip
    assert row.status == "running" and row.g == "2" and row.finished_at is None
    assert float(row.cost_usd) == 0.1  # money already spent is kept


def test_a_failed_stage_keeps_the_error_type_only(engine, tmp_path):
    prepare(engine, tmp_path)
    run = start_run(engine, "embed corpus", "idx-test-3", {}, 1.0, sample=False)
    begin_stage(engine, run, "extract", 5)
    end_stage(engine, run, "extract", 2, 0.01, error="ConnectionError")
    stage = one(engine, "SELECT status, error FROM run_stages WHERE run_id = :id", id=run.id)
    assert tuple(stage) == ("failed", "ConnectionError")


def test_unknown_corpus_and_status_are_refused(engine, tmp_path):
    with pytest.raises(ValueError, match="corpus not found"):
        start_run(engine, "no such corpus", "v", {}, 1.0, sample=False)
    prepare(engine, tmp_path)
    run = start_run(engine, "embed corpus", "idx-test-4", {}, 1.0, sample=False)
    with pytest.raises(ValueError, match="unexpected run status"):
        finish_run(engine, run, "published", 0, 0, 0, {})


def test_estimate_counts_prompts_exactly_and_grows_with_gleaning():
    units = [{"id": "u", "title": "T", "section": "Intro", "text": "word " * 200}] * 10
    zero, two = estimate_cost(units, ONTOLOGY, "gpt-4.1-mini")
    assert zero["gleaning_passes"] == 0 and two["gleaning_passes"] == 2
    assert two["estimated_cost_usd"] > 2 * zero["estimated_cost_usd"]
    assert zero["tokens_out"] == 10 * 350
    assert estimate_cost(units, ONTOLOGY, "some-future-model")[0]["estimated_cost_usd"] is None
