import uuid

import pytest

from agriworldmodel.evidence.schemas import EvidenceSourceCreate, EvidenceSourceType
from agriworldmodel.evidence.service import register_evidence_source
from agriworldmodel.retrieval.dense import (
    DenseRetrievalError,
    embed_chunk, search_dense_chunks, search_dense_text, store_chunk_embedding
)
from agriworldmodel.retrieval.embedding import EMBEDDING_DIMENSION
from agriworldmodel.retrieval.ingestion import register_knowledge_chunk
from agriworldmodel.retrieval.schemas import KnowledgeChunkCreate

def vector_at(index: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[index] = 1.0
    return vector

class FakeEmbedder:
    model_name = "fixture-embedder"
    dimension = EMBEDDING_DIMENSION

    def embed_documents(
        self, texts: list[str],
    ) -> list[list[float]]:
        return [
            (
                vector_at(0)
                if "nitrogen" in text.lower()
                else vector_at(1)
            )
            for text in texts
        ]

    def embed_query(
        self, text: str,
    ) -> list[float]:
        if "nitrogen" in text.lower():
            return vector_at(0)

        return vector_at(1)


def make_source(db_session):
    return register_evidence_source(
        db_session,
        EvidenceSourceCreate(
            source_type=EvidenceSourceType.LITERATURE,
            title="Synthetic Dense Source",
            publisher="Fixture Publisher",
            published_year=2026,
        ),
    )

def make_chunk(
    db_session, source, *,
    index: int,
    content: str,
    crop: str | None = None,
):
    return register_knowledge_chunk(
        db_session,
        KnowledgeChunkCreate(
            source_id=source.id,
            chunk_index=index,
            content=content,
            locator=f"p. {index + 1}",
            crop=crop,
        ),
    )

# -------------------------------------------------------------------
# 1. Invalid embedding dimensions must be rejected.
# -------------------------------------------------------------------
def test_embedding_dimension_is_validated(db_session):
    source = make_source(db_session)

    chunk = make_chunk(
        db_session, source,
        index=0, content="Fixture content."
    )

    with pytest.raises(DenseRetrievalError):
        store_chunk_embedding(
            db_session,
            chunk_id=chunk.id,
            embedding=[1.0, 0.0],
            model_name="broken-fixture",
        )

# -------------------------------------------------------------------
# 2. A chunk can be embedded through an embedder boundary.
# -------------------------------------------------------------------
def test_embed_chunk_stores_vector_and_model(db_session):
    source = make_source(db_session)

    chunk = make_chunk(
        db_session, source,
        index=0, content="Synthetic nitrogen fixture.",
    )

    embedder = FakeEmbedder()

    saved = embed_chunk(db_session, chunk_id=chunk.id, embedder=embedder)

    assert saved.embedding is not None
    assert saved.embedding_model == "fixture-embedder"
    assert len(saved.embedding) == 1024

# -------------------------------------------------------------------
# 3. Dense retrieval ranks the closest vector first.
# -------------------------------------------------------------------
def test_dense_retrieval_ranks_nearest_chunk(db_session):
    source = make_source(db_session)

    relevant = make_chunk(
        db_session, source,
        index=0, content="Relevant fixture."
    )

    unrelated = make_chunk(
        db_session, source,
        index=1, content="Unrelated fixture."
    )

    store_chunk_embedding(
        db_session,
        chunk_id=relevant.id,
        embedding=vector_at(0),
        model_name="fixture-embedder",
    )

    store_chunk_embedding(
        db_session,
        chunk_id=unrelated.id,
        embedding=vector_at(1),
        model_name="fixture-embedder",
    )

    results = search_dense_chunks(
        db_session,
        query_embedding=vector_at(0),
        embedding_model="fixture-embedder",
    )

    assert len(results) == 2
    assert results[0].chunk_id == relevant.id
    assert results[0].score > results[1].score

# -------------------------------------------------------------------
# 4. Dense retrieval respects crop scope.
# -------------------------------------------------------------------
def test_dense_retrieval_respects_crop_scope(db_session):
    source = make_source(db_session)
    durian = make_chunk(
        db_session, source, index=0,
        content="Durian fixture.", crop="durian"
    )

    rice = make_chunk(
        db_session, source, index=1,
        content="Rice fixture.", crop="rice"
    )

    for chunk in [durian, rice]:
        store_chunk_embedding(
            db_session,
            chunk_id=chunk.id,
            embedding=vector_at(0),
            model_name="fixture-embedder"
        )

    results = search_dense_chunks(
        db_session,
        query_embedding=vector_at(0),
        crop="durian",
        embedding_model="fixture-embedder"
    )

    assert len(results) == 1
    assert results[0].chunk_id == durian.id

# -------------------------------------------------------------------
# 5. Text retrieval uses the embedder and keeps provenance.
# -------------------------------------------------------------------
def test_dense_text_search_uses_embedder(db_session):
    source = make_source(db_session)
    nitrogen = make_chunk(
        db_session, source,
        index=0, content="Synthetic nitrogen fixture."
    )

    unrelated = make_chunk(
        db_session, source,
        index=1, content="Synthetic irrigation fixture."
    )

    embedder = FakeEmbedder()

    embed_chunk(
        db_session,
        chunk_id=nitrogen.id,
        embedder=embedder,
    )

    embed_chunk(
        db_session,
        chunk_id=unrelated.id,
        embedder=embedder,
    )

    results = search_dense_text(
        db_session,
        query_text="nitrogen requirement",
        embedder=embedder,
    )

    assert len(results) == 2
    assert results[0].chunk_id == nitrogen.id
    assert results[0].source_id == source.id