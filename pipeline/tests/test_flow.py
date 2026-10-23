"""Flow tests. Embeddings are MOCKS (FakeEmbedder); PDFs are small real files; Postgres and
Qdrant are the real containers (own throwaway database and collection)."""

import csv
import hashlib
import os
import textwrap
import uuid

import pytest
from prefect.testing.utilities import prefect_test_harness
from qdrant_client import QdrantClient
from sqlalchemy import text

from graphlens_pipeline import flow as flow_module
from graphlens_pipeline.embed import collection_name
from tests.conftest import fake_pages, make_text_pdf
from tests.test_embed import FakeEmbedder
from tests.test_ingest import FIELDS, reset

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def prefect_harness():
    with prefect_test_harness():
        yield


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch):
    """Retries are kept, but without the 5 second pause, so tests stay fast."""
    monkeypatch.setattr(
        flow_module, "ingest_stage", flow_module.ingest_stage.with_options(retry_delay_seconds=0)
    )
    monkeypatch.setattr(
        flow_module, "embed_stage", flow_module.embed_stage.with_options(retry_delay_seconds=0)
    )


class FlakyEmbedder(FakeEmbedder):
    """MOCK that fails once, on its second call, to imitate a dropped connection."""

    def __init__(self):
        super().__init__()
        self.failed = False
        self.batches = 0

    def dense(self, texts):
        self.batches += 1
        if self.batches == 2 and not self.failed:
            self.failed = True
            raise ConnectionError("simulated dropped connection")
        return super().dense(texts)


def write_pdf_corpus(root, names, licenses=None):
    """Real, tiny PDFs (the extractor really runs) and a manifest for them."""
    licenses = licenses or {}
    pdf_dir = root / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in names:
        lines = []
        for page in fake_pages(name, body_sentences=30):
            for line in page.splitlines():  # keep headings on their own line
                lines += textwrap.wrap(line, 90)
        make_text_pdf(pdf_dir / f"{name}.pdf", [ln for ln in lines if ln])
        sha = hashlib.sha256((pdf_dir / f"{name}.pdf").read_bytes()).hexdigest()
        rows.append({
            "paper_id": name, "title": f"Title {name}", "year": "2023", "venue": "ACL",
            "authors": "A", "pdf_url": f"https://example.org/{name}.pdf", "page_url": "",
            "license": licenses.get(name, "CC BY 4.0"), "license_basis_url": "", "retrieved_on": "",
            "sha256": sha, "bytes": "0",
        })  # fmt: skip
    manifest = root / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return manifest, pdf_dir


@pytest.fixture
def setup(engine, tmp_path):
    reset(engine)
    client = QdrantClient(url=os.environ["QDRANT_URL"])
    slug = f"t{uuid.uuid4().hex[:8]}"
    yield engine, client, slug, tmp_path
    name = collection_name(slug, "v1")
    if client.collection_exists(name):
        client.delete_collection(name)


def run_flow(engine, slug, manifest, pdf_dir, batch_size=4):
    return flow_module.index_baseline(
        engine.url.render_as_string(hide_password=False), os.environ["QDRANT_URL"],
        str(manifest), str(pdf_dir), "flow corpus", "d", slug, "v1",
        make_live=False, batch_size=batch_size,
    )  # fmt: skip


def count(engine, table):
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def test_flow_ingests_then_embeds_and_a_second_run_adds_nothing(setup, monkeypatch):
    engine, client, slug, root = setup
    monkeypatch.setattr(flow_module, "EMBEDDER_FACTORY", FakeEmbedder)
    manifest, pdf_dir = write_pdf_corpus(root, ["p1", "p2"])

    first = run_flow(engine, slug, manifest, pdf_dir)
    units = count(engine, "text_units")
    assert first["ingest"]["ingested"] == 2 and not first["ingest"]["failures"]
    assert first["embed"]["embedded"] == units > 4
    assert client.count(first["embed"]["collection"], exact=True).count == units

    second = run_flow(engine, slug, manifest, pdf_dir)
    assert second["ingest"]["ingested"] == 0 and second["ingest"]["skipped"] == 2
    assert second["embed"]["embedded"] == 0 and second["embed"]["skipped"] == units
    assert count(engine, "text_units") == units


def test_a_dropped_connection_is_retried_without_repeating_finished_work(setup, monkeypatch):
    engine, client, slug, root = setup
    embedder = FlakyEmbedder()
    monkeypatch.setattr(flow_module, "EMBEDDER_FACTORY", lambda: embedder)
    manifest, pdf_dir = write_pdf_corpus(root, ["p1", "p2"])

    result = run_flow(engine, slug, manifest, pdf_dir, batch_size=4)
    units = count(engine, "text_units")

    assert embedder.failed  # the failure really happened
    assert client.count(result["embed"]["collection"], exact=True).count == units
    # The first batch survived the failure: the retry skipped it, so no unit was embedded twice.
    assert result["embed"]["skipped"] == 4
    assert result["embed"]["embedded"] == units - 4
    assert embedder.calls == units  # texts sent to the model in total, none repeated


def test_a_bad_paper_is_reported_and_the_rest_still_flows(setup, monkeypatch):
    engine, client, slug, root = setup
    monkeypatch.setattr(flow_module, "EMBEDDER_FACTORY", FakeEmbedder)
    manifest, pdf_dir = write_pdf_corpus(root, ["good", "nc"], licenses={"nc": "CC BY-NC 4.0"})

    result = run_flow(engine, slug, manifest, pdf_dir)

    assert set(result["ingest"]["failures"]) == {"nc"}
    assert result["ingest"]["ingested"] == 1
    assert result["embed"]["embedded"] == count(engine, "text_units") > 0
