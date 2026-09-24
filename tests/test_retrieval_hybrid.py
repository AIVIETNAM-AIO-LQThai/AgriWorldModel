import uuid

import pytest

from agriworldmodel.evidence.schemas import EvidenceSourceCreate, EvidenceSourceType
from agriworldmodel.evidence.service import register_evidence_source
from agriworldmodel.retrieval.dense import embed_chunk
from agriworldmodel.retrieval.embedding import EMBEDDING_DIMENSION
from agriworldmodel.retrieval.hybrid import fuse_ranked_chunks, search_hybrid_chunks
from agriworldmodel.retrieval.ingestion import register_knowledge_chunk
from agriworldmodel.retrieval.schemas import KnowledgeChunkCreate, RetrievedChunk

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

def retrieved(
    *, chunk_id: uuid.UUID, score: float,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        source_id=uuid.uuid4(),
        source_type="literature",
        source_title="Fixture Source",
        chunk_index=0,
        content="Fixture content",
        locator="p. 1",
        score=score,
    )

# -------------------------------------------------------------------
# 1. RRF should reward agreement between lexical and dense retrieval.
# -------------------------------------------------------------------
def test_rrf_rewards_agreement_between_retrievers():
    shared = uuid.uuid4()
    lexical_only = uuid.uuid4()
    dense_only = uuid.uuid4()

    lexical = [
        retrieved(chunk_id=lexical_only,score=0.9),
        retrieved(chunk_id=shared, score=0.8),
    ]
    dense = [
        retrieved(chunk_id=dense_only, score=0.95),
        retrieved(chunk_id=shared, score=0.90),
    ]
    results = fuse_ranked_chunks(lexical_results=lexical, dense_results=dense)

    assert results[0].chunk_id == shared
    assert results[0].lexical_rank == 2
    assert results[0].dense_rank == 2

# -------------------------------------------------------------------
# 2. RRF should preserve candidates found by only one retriever.
# -------------------------------------------------------------------
def test_rrf_keeps_single_retriever_candidates():
    lexical_id = uuid.uuid4()
    dense_id = uuid.uuid4()

    results = fuse_ranked_chunks(
        lexical_results=[
            retrieved(chunk_id=lexical_id, score=0.7)
        ],
        dense_results=[
            retrieved(chunk_id=dense_id, score=0.8)
        ],
    )

    ids = {
        result.chunk_id for result in results
    }

    assert lexical_id in ids
    assert dense_id in ids

# -------------------------------------------------------------------
# 3. RRF should depend on rank positions, not raw score magnitudes.
# -------------------------------------------------------------------
def test_rrf_uses_rank_not_raw_score_scale():
    first = uuid.uuid4()
    second = uuid.uuid4()

    lexical = [
        retrieved(chunk_id=first, score=0.0001),
        retrieved(chunk_id=second, score=999999.0),
    ]

    results = fuse_ranked_chunks(
        lexical_results=lexical,
        dense_results=[],
    )

    assert results[0].chunk_id == first

# -------------------------------------------------------------------
# 4. Hybrid search should combine lexical and dense retrieval.
# -------------------------------------------------------------------
def make_source(db_session):
    return register_evidence_source(
        db_session,
        EvidenceSourceCreate(
            source_type=(
                EvidenceSourceType.LITERATURE
            ),
            title="Hybrid Fixture Source",
            publisher="Fixture Publisher",
            published_year=2026,
        ),
    )

def make_chunk(
    db_session, source, *,
    index: int, content: str,
    crop: str | None = None,
):
    return register_knowledge_chunk(
        db_session,
        KnowledgeChunkCreate(
            source_id=source.id,
            chunk_index=index,
            content=content,
            locator=f"p. {index + 1}",
            crop=crop
        ),
    )

def test_hybrid_search_combines_lexical_and_dense(db_session):
    source = make_source(db_session)

    nitrogen = make_chunk(
        db_session, source,
        index=0, content="Synthetic nitrogen uptake fixture."
    )
    irrigation = make_chunk(
        db_session, source,
        index=1, content="Synthetic irrigation scheduling fixture."
    )

    embedder = FakeEmbedder()

    embed_chunk(
        db_session,
        chunk_id=nitrogen.id,
        embedder=embedder,
    )
    embed_chunk(
        db_session,
        chunk_id=irrigation.id,
        embedder=embedder,
    )

    results = search_hybrid_chunks(
        db_session,
        query_text="nitrogen uptake",
        embedder=embedder,
    )

    assert len(results) >= 1
    assert results[0].chunk_id == nitrogen.id
    assert results[0].lexical_rank is not None
    assert results[0].dense_rank is not None

# -------------------------------------------------------------------
# 5. Hybrid retrieval must preserve crop isolation.
# -------------------------------------------------------------------
def test_hybrid_search_respects_crop_scope(db_session):
    source = make_source(db_session)

    durian = make_chunk(
        db_session, source, index=0,
        content="Synthetic nitrogen fixture.", crop="durian",
    )
    rice = make_chunk(
        db_session, source, index=1,
        content="Synthetic nitrogen fixture.", crop="rice",
    )

    embedder = FakeEmbedder()

    for chunk in [durian, rice]:
        embed_chunk(
            db_session,
            chunk_id=chunk.id,
            embedder=embedder,
        )

    results = search_hybrid_chunks(
        db_session,
        query_text="nitrogen fixture",
        embedder=embedder,
        crop="durian",
    )

    assert len(results) == 1
    assert results[0].chunk_id == durian.id