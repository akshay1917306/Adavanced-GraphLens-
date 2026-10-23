"""Embedding tests.

Most tests use a MOCK embedder (clearly named FakeEmbedder) so they are fast and exact.
`test_real_models_*` load the real local models and check that they behave sensibly.
Qdrant tests use their own uniquely named collections and alias, never the real ones.
"""

import hashlib
import math
import os
import uuid
import zlib

import pytest
from qdrant_client import QdrantClient

from graphlens_pipeline.embed import (
    DENSE_DIM,
    MAX_INPUT_TOKENS,
    FastEmbedder,
    collection_name,
    embed_corpus,
    ensure_collection,
    point_id,
    slugify,
)
from graphlens_pipeline.ingest import ingest_manifest
from tests.conftest import fake_pages
from tests.test_ingest import extractor, reset, write_corpus


class FakeEmbedder:
    """MOCK: deterministic fake vectors, no model. Counts how often it is called."""

    def __init__(self, long_units: bool = False) -> None:
        self.calls = 0
        self.long_units = long_units

    def dense(self, texts):
        self.calls += len(texts)
        return [self._vector(t) for t in texts]

    def sparse(self, texts):
        out = []
        for t in texts:
            indices = sorted({zlib.crc32(w.encode()) % 10000 for w in t.split()}) or [0]
            out.append((indices, [1.0] * len(indices)))
        return out

    def token_counts(self, texts):
        return [MAX_INPUT_TOKENS + 1 if self.long_units else 100 for _ in texts]

    @staticmethod
    def _vector(text):
        seed = hashlib.sha256(text.encode()).digest()
        raw = [seed[i % len(seed)] / 255 for i in range(DENSE_DIM)]
        norm = math.sqrt(sum(x * x for x in raw))
        return [x / norm for x in raw]


@pytest.fixture
def qdrant():
    """A Qdrant client plus a list of collections to delete afterwards (this also removes
    any alias that points at them)."""
    url = os.environ.get("QDRANT_URL")
    if not url:
        pytest.skip("needs QDRANT_URL (run through docker compose)")
    client = QdrantClient(url=url)
    created: list[str] = []
    yield client, created
    for name in created:
        client.delete_collection(name)


def prepare(engine, tmp_path, papers=("p1", "p2")):
    reset(engine)
    manifest, pdf_dir = write_corpus(tmp_path, {p: {} for p in papers})
    pages = {p: fake_pages(p) for p in papers}
    ingest_manifest(engine, manifest, pdf_dir, "embed corpus", "d", extractor(pages))


def test_naming_and_ids_are_stable():
    assert slugify("QA papers (ACL)!") == "qa_papers_acl"
    assert collection_name("qa_v0", "baseline-1") == "units_qa_v0_baseline_1"
    assert point_id("u_abc_0001") == point_id("u_abc_0001")
    assert point_id("u_abc_0001") != point_id("u_abc_0002")
    uuid.UUID(point_id("u_abc_0001"))  # a valid UUID, as Qdrant requires


@pytest.mark.integration
def test_embeds_every_unit_and_keeps_text_out_of_qdrant(engine, qdrant, tmp_path):
    client, created = qdrant
    prepare(engine, tmp_path)
    slug = f"t{uuid.uuid4().hex[:8]}"
    report = embed_corpus(engine, client, "embed corpus", slug, "v1", FakeEmbedder())
    created.append(report.collection)

    assert report.embedded > 4 and report.skipped == 0
    assert client.count(report.collection, exact=True).count == report.embedded
    point = client.scroll(report.collection, limit=1, with_payload=True)[0][0]
    assert set(point.payload) == {
        "unit_id", "document_id", "ordinal", "section", "corpus_id", "index_version",
    }  # fmt: skip
    assert "text" not in point.payload  # text stays in Postgres
    assert point.payload["index_version"] == "v1"
    assert point.payload["section"]


@pytest.mark.integration
def test_running_twice_embeds_nothing_new(engine, qdrant, tmp_path):
    client, created = qdrant
    prepare(engine, tmp_path)
    slug = f"t{uuid.uuid4().hex[:8]}"
    embedder = FakeEmbedder()
    first = embed_corpus(engine, client, "embed corpus", slug, "v1", embedder)
    created.append(first.collection)
    calls_after_first = embedder.calls
    second = embed_corpus(engine, client, "embed corpus", slug, "v1", embedder)

    assert second.embedded == 0 and second.skipped == first.embedded
    assert embedder.calls == calls_after_first  # the model was not asked again
    assert client.count(first.collection, exact=True).count == first.embedded


@pytest.mark.integration
def test_units_over_the_model_limit_are_reported(engine, qdrant, tmp_path):
    client, created = qdrant
    prepare(engine, tmp_path, papers=("p1",))
    slug = f"t{uuid.uuid4().hex[:8]}"
    report = embed_corpus(engine, client, "embed corpus", slug, "v1", FakeEmbedder(long_units=True))
    created.append(report.collection)
    assert report.truncated == report.embedded > 0


@pytest.mark.integration
def test_live_alias_points_at_the_collection(engine, qdrant, tmp_path):
    client, created = qdrant
    prepare(engine, tmp_path, papers=("p1",))
    slug = f"t{uuid.uuid4().hex[:8]}"
    alias = f"test_alias_{uuid.uuid4().hex[:8]}"
    report = embed_corpus(
        engine, client, "embed corpus", slug, "v1", FakeEmbedder(),
        make_live=True, alias=alias,
    )  # fmt: skip
    created.append(report.collection)
    found = {a.alias_name: a.collection_name for a in client.get_aliases().aliases}
    assert found[alias] == report.collection
    # Moving the alias again must work (delete and create in one step).
    embed_corpus(
        engine, client, "embed corpus", slug, "v1", FakeEmbedder(), make_live=True, alias=alias
    )


@pytest.mark.integration
def test_collection_with_wrong_vector_size_is_refused(qdrant):
    client, created = qdrant
    name = f"units_t{uuid.uuid4().hex[:8]}_wrong"
    from qdrant_client import models

    client.create_collection(
        name,
        vectors_config={"dense": models.VectorParams(size=10, distance=models.Distance.COSINE)},
    )
    created.append(name)
    with pytest.raises(ValueError, match="vector size"):
        ensure_collection(client, name)


@pytest.mark.model
def test_real_models_give_sensible_vectors():
    embedder = FastEmbedder()
    question = "How fast is the new retrieval method?"
    similar = "How quickly does the new approach for finding documents run?"
    unrelated = "The recipe needs two cups of flour and a pinch of salt."
    q, s, u = embedder.dense([question, similar, unrelated])

    def cosine(a, b):
        return sum(x * y for x, y in zip(a, b, strict=True))  # vectors are normalised

    assert len(q) == DENSE_DIM
    assert cosine(q, s) > cosine(q, u) + 0.1

    ((indices, values),) = embedder.sparse(["HopFuse improves on LatticeRank"])
    assert len(indices) == len(values) >= 2
    assert all(v > 0 for v in values)

    assert len(embedder.dense_query("What is HopFuse?")) == DENSE_DIM
    q_indices, q_values = embedder.sparse_query("What is HopFuse?")
    assert q_indices and len(q_indices) == len(q_values)

    short, long = embedder.token_counts(["a short sentence", "word " * 700])
    assert short < 10 and long > MAX_INPUT_TOKENS
