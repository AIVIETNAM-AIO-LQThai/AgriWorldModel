from sqlalchemy.orm import Session

from agriworldmodel.retrieval.embedding import DenseEmbedder
from agriworldmodel.retrieval.hybrid import DEFAULT_RRF_K, search_hybrid_chunks
from agriworldmodel.retrieval.reranker import Reranker
from agriworldmodel.retrieval.schemas import HybridRetrievedChunk, RerankedChunk

class RerankingError(ValueError):
    pass

def rerank_hybrid_chunks(
    *, query_text: str,
    candidates: list[HybridRetrievedChunk],
    reranker: Reranker, limit: int = 10
) -> list[RerankedChunk]:
    """
    Rerank already-retrieved hybrid candidates.

    The reranker changes ordering only. Existing retrieval
    provenance and diagnostic scores are preserved.
    """
    if limit <= 0:
        return []
    if not query_text.strip():
        return []
    if not candidates:
        return []

    passages = [
        candidate.content for candidate in candidates
    ]

    scores = reranker.score(
        query=query_text, passages=passages
    )

    if len(scores) != len(candidates):
        raise RerankingError(
            "Reranker returned a different number of scores than candidates."
        )

    reranked = [
        RerankedChunk(
            **candidate.model_dump(),
            hybrid_rank=hybrid_rank,
            rerank_score=float(score),
        )
        for hybrid_rank, (candidate, score)
        in enumerate(
            zip(candidates, scores), start=1
        )
    ]

    reranked.sort(key=lambda item: (-item.rerank_score, -item.rrf_score, str(item.chunk_id)))
    return reranked[:limit]

def search_reranked_chunks(
    session: Session, *,
    query_text: str,
    embedder: DenseEmbedder, reranker: Reranker,
    crop: str | None = None,
    limit: int = 10, candidate_limit: int = 20,
    rrf_k: int = DEFAULT_RRF_K
) -> list[RerankedChunk]:
    """
    Full retrieval pipeline:

        lexical
          +
        dense
          ↓
         RRF
          ↓
       reranker
    """
    if candidate_limit < limit:
        raise ValueError("candidate_limit must be >= limit.")

    candidates = search_hybrid_chunks(
        session, query_text=query_text,
        embedder=embedder, crop=crop,
        limit=candidate_limit, candidate_limit=candidate_limit,
        rrf_k=rrf_k
    )

    return rerank_hybrid_chunks(
        query_text=query_text,
        candidates=candidates,
        reranker=reranker,
        limit=limit
    )