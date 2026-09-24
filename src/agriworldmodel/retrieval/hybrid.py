import uuid

from sqlalchemy.orm import Session

from agriworldmodel.retrieval.dense import search_dense_text
from agriworldmodel.retrieval.embedding import DenseEmbedder
from agriworldmodel.retrieval.lexical import search_lexical_chunks
from agriworldmodel.retrieval.schemas import HybridRetrievedChunk, RetrievedChunk

DEFAULT_RRF_K = 60

def _rrf_contribution(
    *, rank: int, k: int
) -> float:
    """
    Compute one Reciprocal Rank Fusion contribution.

    Ranks are one-based:

        rank 1 -> 1 / (k + 1)
        rank 2 -> 1 / (k + 2)
        ...
    """
    if rank < 1:
        raise ValueError("Ranks must be >= 1.")
    if k < 1:
        raise ValueError("k must be >= 1.")

    return 1.0 / (k + rank)

def fuse_ranked_chunks(
    *,
    lexical_results: list[RetrievedChunk],
    dense_results: list[RetrievedChunk],
    limit: int = 10, rrf_k: int = DEFAULT_RRF_K
) -> list[HybridRetrievedChunk]:
    """
    Fuse lexical and dense ranked lists using RRF.

    Raw lexical and dense scores are preserved for
    diagnostics but are NOT directly combined.
    """
    if limit <= 0:
        return []

    combined: dict[
        uuid.UUID, HybridRetrievedChunk
    ] = {}

    for rank, result in enumerate(
        lexical_results, start=1
    ):
        combined[result.chunk_id] = (
            HybridRetrievedChunk(
                chunk_id=result.chunk_id,
                source_id=result.source_id,
                source_type=result.source_type,
                source_title=result.source_title,
                chunk_index=result.chunk_index,
                content=result.content,
                locator=result.locator,
                crop=result.crop,
                lexical_rank=rank,
                lexical_score=result.score,
                rrf_score=_rrf_contribution(
                    rank=rank,
                    k=rrf_k,
                )
            )
        )

    for rank, result in enumerate(
        dense_results, start=1
    ):
        contribution = _rrf_contribution(
            rank=rank, k=rrf_k
        )
        existing = combined.get(result.chunk_id)

        if existing is None:
            combined[result.chunk_id] = (
                HybridRetrievedChunk(
                    chunk_id=result.chunk_id,
                    source_id=result.source_id,
                    source_type=result.source_type,
                    source_title=result.source_title,
                    chunk_index=result.chunk_index,
                    content=result.content,
                    locator=result.locator,
                    crop=result.crop,
                    dense_rank=rank,
                    dense_score=result.score,
                    rrf_score=contribution,
                )
            )

        else:
            existing.dense_rank = rank
            existing.dense_score = result.score
            existing.rrf_score += contribution

    results = list(combined.values())
    results.sort(
        key=lambda item: (-item.rrf_score, str(item.chunk_id))
    )

    return results[:limit]

def search_hybrid_chunks(
    session: Session, *,
    query_text: str,
    embedder: DenseEmbedder,
    crop: str | None = None,
    limit: int = 10,
    candidate_limit: int = 20,
    rrf_k: int = DEFAULT_RRF_K
) -> list[HybridRetrievedChunk]:
    """
    Execute lexical + dense retrieval and fuse them
    using Reciprocal Rank Fusion.
    """
    if not query_text.strip():
        return []
    if candidate_limit < limit:
        raise ValueError("candidate_limit must be >= limit.")

    lexical_results = search_lexical_chunks(
        session, query_text=query_text, crop=crop, limit=candidate_limit
    )
    dense_results = search_dense_text(
        session, query_text=query_text, embedder=embedder, crop=crop, limit=candidate_limit
    )

    return fuse_ranked_chunks(
        lexical_results=lexical_results,
        dense_results=dense_results,
        limit=limit, rrf_k=rrf_k
    )