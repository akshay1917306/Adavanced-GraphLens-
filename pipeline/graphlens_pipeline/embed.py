"""Embed text units and store the vectors in Qdrant (dense and sparse, for hybrid search).

Models run locally through fastembed (ONNX), so no API key and no cost:
- dense: BAAI/bge-base-en-v1.5 (768 numbers per unit, MIT license; fastembed ships the
  int8-quantised ONNX file). The model reads at most 512 tokens.
- sparse: Qdrant/bm25, the keyword side. It is what finds exact names such as "HopFuse".

Only vectors and a small payload go to Qdrant. The text stays in Postgres (blueprint 4.5).
Safe to run again: units that already have a point are skipped.
"""

import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from qdrant_client import QdrantClient, models
from sqlalchemy import Engine, text

DENSE_MODEL = "BAAI/bge-base-en-v1.5"
SPARSE_MODEL = "Qdrant/bm25"
DENSE_DIM = 768
MAX_INPUT_TOKENS = 512  # what the dense model reads; longer text is cut
DENSE_NAME = "dense"
SPARSE_NAME = "sparse"
LIVE_ALIAS = "units_live"
# BGE models search better when a short question starts with this sentence. Passages do not.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
POINT_NAMESPACE = uuid.UUID("6f1b6f0e-5b0e-4f0e-9a52-1d2d9d0a7c11")  # fixed, makes IDs stable


class Embedder(Protocol):
    def dense(self, texts: list[str]) -> list[list[float]]: ...
    def sparse(self, texts: list[str]) -> list[tuple[list[int], list[float]]]: ...
    def token_counts(self, texts: list[str]) -> list[int]: ...


class FastEmbedder:
    """The real local models. Loading takes a few seconds."""

    def __init__(self) -> None:
        from fastembed import SparseTextEmbedding, TextEmbedding
        from tokenizers import Tokenizer

        self._dense = TextEmbedding(DENSE_MODEL)
        self._sparse = SparseTextEmbedding(SPARSE_MODEL)
        self._tokenizer = Tokenizer.from_pretrained(DENSE_MODEL)
        self._tokenizer.no_truncation()

    def dense(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._dense.embed(texts)]

    def sparse(self, texts: list[str]) -> list[tuple[list[int], list[float]]]:
        return [(e.indices.tolist(), e.values.tolist()) for e in self._sparse.embed(texts)]

    def token_counts(self, texts: list[str]) -> list[int]:
        return [len(self._tokenizer.encode(t).ids) for t in texts]

    def dense_query(self, question: str) -> list[float]:
        """Embed a search question (BGE wants its instruction sentence in front)."""
        return next(iter(self._dense.embed([QUERY_PREFIX + question]))).tolist()

    def sparse_query(self, question: str) -> tuple[list[int], list[float]]:
        embedding = next(iter(self._sparse.query_embed(question)))
        return embedding.indices.tolist(), embedding.values.tolist()


@dataclass
class EmbedReport:
    collection: str
    embedded: int = 0
    skipped: int = 0
    truncated: int = 0  # units longer than the dense model's input (their tail is not embedded)


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "corpus"


def collection_name(corpus_slug: str, index_version: str) -> str:
    """Blueprint 4.5: units_{corpus_slug}_{index_version}."""
    return f"units_{slugify(corpus_slug)}_{slugify(index_version)}"


def point_id(unit_id: str) -> str:
    return str(uuid.uuid5(POINT_NAMESPACE, unit_id))


def ensure_collection(client: QdrantClient, name: str) -> None:
    if client.collection_exists(name):
        info = client.get_collection(name)
        size = info.config.params.vectors[DENSE_NAME].size  # type: ignore[index]
        if size != DENSE_DIM:
            raise ValueError(f"collection {name} has vector size {size}, expected {DENSE_DIM}")
        return
    client.create_collection(
        collection_name=name,
        vectors_config={
            DENSE_NAME: models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE)
        },
        sparse_vectors_config={
            SPARSE_NAME: models.SparseVectorParams(modifier=models.Modifier.IDF)
        },
    )


def set_live_alias(client: QdrantClient, name: str, alias: str = LIVE_ALIAS) -> None:
    """Point the alias (`units_live`) at this collection in one step, so searches see no gap."""
    operations: list[models.AliasOperations] = []
    if any(a.alias_name == alias for a in client.get_aliases().aliases):
        operations.append(
            models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name=alias))
        )
    operations.append(
        models.CreateAliasOperation(
            create_alias=models.CreateAlias(collection_name=name, alias_name=alias)
        )
    )
    client.update_collection_aliases(change_aliases_operations=operations)


def _batches(items: list, size: int) -> Iterator[list]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def embed_corpus(
    engine: Engine,
    client: QdrantClient,
    corpus_name: str,
    corpus_slug: str,
    index_version: str,
    embedder: Embedder,
    batch_size: int = 32,
    make_live: bool = False,
    alias: str = LIVE_ALIAS,
) -> EmbedReport:
    """Embed every text unit of a corpus that is not in Qdrant yet."""
    name = collection_name(corpus_slug, index_version)
    ensure_collection(client, name)
    report = EmbedReport(collection=name)

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT u.id, u.document_id, u.ordinal, u.text, d.corpus_id,"
                " d.metadata->'unit_sections'->>u.ordinal AS section"
                " FROM text_units u JOIN documents d ON d.id = u.document_id"
                " JOIN corpora c ON c.id = d.corpus_id WHERE c.name = :name ORDER BY u.id"
            ),
            {"name": corpus_name},
        ).all()

    for batch in _batches(rows, batch_size):
        ids = [point_id(row.id) for row in batch]
        existing = {
            str(point.id)
            for point in client.retrieve(name, ids=ids, with_payload=False, with_vectors=False)
        }
        todo = [(pid, row) for pid, row in zip(ids, batch, strict=True) if pid not in existing]
        report.skipped += len(batch) - len(todo)
        if not todo:
            continue
        texts = [row.text for _, row in todo]
        dense = embedder.dense(texts)
        sparse = embedder.sparse(texts)
        report.truncated += sum(1 for n in embedder.token_counts(texts) if n > MAX_INPUT_TOKENS)
        points = [
            models.PointStruct(
                id=pid,
                vector={
                    DENSE_NAME: dense_vector,
                    SPARSE_NAME: models.SparseVector(indices=indices, values=values),
                },
                payload={
                    "unit_id": row.id,
                    "document_id": str(row.document_id),
                    "ordinal": row.ordinal,
                    "section": row.section,
                    "corpus_id": str(row.corpus_id),
                    "index_version": index_version,
                },
            )
            for (pid, row), dense_vector, (indices, values) in zip(todo, dense, sparse, strict=True)
        ]
        client.upsert(collection_name=name, points=points, wait=True)
        report.embedded += len(points)

    if make_live:
        set_live_alias(client, name, alias)
    return report
