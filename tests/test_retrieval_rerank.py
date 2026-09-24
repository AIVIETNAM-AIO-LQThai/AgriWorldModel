import uuid

import pytest

from agriworldmodel.evidence.schemas import EvidenceSourceCreate, EvidenceSourceType
from agriworldmodel.evidence.service import register_evidence_source
from agriworldmodel.retrieval.dense import embed_chunk
from agriworldmodel.retrieval.embedding import EMBEDDING_DIMENSION
from agriworldmodel.retrieval.ingestion import register_knowledge_chunk
from agriworldmodel.retrieval.rerank import RerankingError, rerank_hybrid_chunks, search_reranked_chunks
from agriworldmodel.retrieval.schemas import HybridRetrievedChunk, KnowledgeChunkCreate

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

class FakeReranker:
    model_name = "fixture-reranker"

    def score(
        self,
        *,
        query: str,
        passages: list[str],
    ) -> list[float]:
        return [
            (
                0.95
                if "preferred" in passage.lower()
                else 0.10
            )
            for passage in passages
        ]

def hybrid_candidate(
    *, chunk_id: uuid.UUID, content: str, rrf_score: float,
) -> HybridRetrievedChunk:
    return HybridRetrievedChunk(
        chunk_id=chunk_id,
        source_id=uuid.uuid4(),
        source_type="literature",
        source_title="Fixture Source",
        chunk_index=0,
        content=content,
        locator="p. 1",
        rrf_score=rrf_score,
    )

# -------------------------------------------------------------------
# 1. Reranking should be allowed to change the hybrid RRF ordering.
# -------------------------------------------------------------------
def test_reranker_can_change_hybrid_order():
    hybrid_first = uuid.uuid4()
    preferred = uuid.uuid4()

    candidates = [
        hybrid_candidate(
            chunk_id=hybrid_first,
            content="Ordinary fixture passage.",
            rrf_score=0.05,
        ),
        hybrid_candidate(
            chunk_id=preferred,
            content="Preferred fixture passage.",
            rrf_score=0.04,
        ),
    ]

    results = rerank_hybrid_chunks(
        query_text="fixture query",
        candidates=candidates,
        reranker=FakeReranker(),
    )

    assert results[0].chunk_id == preferred
    assert results[0].hybrid_rank == 2
    assert results[0].rerank_score == 0.95

# -------------------------------------------------------------------
# 2. Reranking must preserve hybrid retrieval diagnostics.
# -------------------------------------------------------------------
def test_reranking_preserves_hybrid_diagnostics():
    chunk_id = uuid.uuid4()

    candidate = HybridRetrievedChunk(
        chunk_id=chunk_id,
        source_id=uuid.uuid4(),
        source_type="literature",
        source_title="Fixture Source",
        chunk_index=3,
        content="Preferred fixture passage.",
        locator="Section 3",
        lexical_rank=2,
        dense_rank=4,
        lexical_score=0.4,
        dense_score=0.8,
        rrf_score=0.031,
    )

    results = rerank_hybrid_chunks(
        query_text="fixture query",
        candidates=[candidate],
        reranker=FakeReranker(),
    )

    result = results[0]

    assert result.lexical_rank == 2
    assert result.dense_rank == 4
    assert result.rrf_score == 0.031
    assert result.locator == "Section 3"

# -------------------------------------------------------------------
# 3. A malformed reranker response must not silently corrupt ranking.
# -------------------------------------------------------------------
def test_reranker_score_count_is_validated():
    class BrokenReranker:
        model_name = "broken"

        def score(
            self, *, query: str, passages: list[str],
        ) -> list[float]:
            return []

    candidates = [
        hybrid_candidate(
            chunk_id=uuid.uuid4(),
            content="Fixture passage.",
            rrf_score=0.02,
        )
    ]

    with pytest.raises(RerankingError):
        rerank_hybrid_chunks(
            query_text="fixture query",
            candidates=candidates,
            reranker=BrokenReranker(),
        )

# -------------------------------------------------------------------
# 4. Reranking should return only the requested final top-k.
# -------------------------------------------------------------------
def test_reranking_applies_final_limit():
    candidates = [
        hybrid_candidate(
            chunk_id=uuid.uuid4(),
            content=f"Preferred fixture {index}",
            rrf_score=0.05 - index * 0.001,
        )
        for index in range(5)
    ]

    results = rerank_hybrid_chunks(
        query_text="fixture query",
        candidates=candidates,
        reranker=FakeReranker(),
        limit=2,
    )

    assert len(results) == 2

def make_source(db_session):
    return register_evidence_source(
        db_session,
        EvidenceSourceCreate(
            source_type=(
                EvidenceSourceType.LITERATURE
            ),
            title="Reranking Fixture Source",
            publisher="Fixture Publisher",
            published_year=2026,
        ),
    )


def make_chunk(
    db_session, source, *,
    index: int, content: str, crop: str | None = None,
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
# 5. The complete retrieval path should end in reranked candidates.
# -------------------------------------------------------------------
def test_search_reranked_chunks_runs_full_pipeline(db_session):
    source = make_source(db_session)
    ordinary = make_chunk(
        db_session, source,
        index=0, content="Synthetic nitrogen ordinary fixture.",
    )
    preferred = make_chunk(
        db_session, source,
        index=1, content="Synthetic nitrogen preferred fixture.",
    )

    embedder = FakeEmbedder()

    for chunk in [ordinary, preferred]:
        embed_chunk(db_session, chunk_id=chunk.id, embedder=embedder)

    results = search_reranked_chunks(
        db_session,
        query_text="nitrogen fixture",
        embedder=embedder,
        reranker=FakeReranker(),
    )

    assert len(results) == 2
    assert results[0].chunk_id == preferred.id
    assert results[0].rerank_score == 0.95