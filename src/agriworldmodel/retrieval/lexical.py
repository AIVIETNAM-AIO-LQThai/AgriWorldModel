from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from agriworldmodel.db.models.evidence_source import EvidenceSource
from agriworldmodel.db.models.knowledge_chunk import KnowledgeChunk
from agriworldmodel.retrieval.schemas import RetrievedChunk

def search_lexical_chunks(
    session: Session, *,
    query_text: str,
    crop: str | None = None,
    limit: int = 10,
) -> list[RetrievedChunk]:
    """
    Retrieve source chunks using PostgreSQL full-text search.

    Crop scoping:
        crop-specific query includes
        - globally scoped chunks (crop=None)
        - chunks for the requested crop

    but excludes chunks belonging to other crops.
    """
    if not query_text.strip():
        return []

    ts_query = func.websearch_to_tsquery(
        "simple", query_text,
    )

    rank = func.ts_rank_cd(
        KnowledgeChunk.search_vector, ts_query,
    ).label("score")

    stmt = (
        select(KnowledgeChunk, EvidenceSource, rank)
        .join(
            EvidenceSource,
            KnowledgeChunk.source_id == EvidenceSource.id,
        )
        .where(KnowledgeChunk.search_vector.op("@@")(ts_query))
    )

    if crop is not None:
        stmt = stmt.where(
            or_(
                KnowledgeChunk.crop.is_(None),
                func.lower(KnowledgeChunk.crop) == crop.lower(),
            )
        )

    stmt = (
        stmt
        .order_by(
            rank.desc(), KnowledgeChunk.id.asc(),
        ).limit(limit)
    )

    rows = session.execute(stmt).all()

    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            source_id=source.id,
            source_type=source.source_type,
            source_title=source.title,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            locator=chunk.locator,
            crop=chunk.crop,
            score=float(score),
        )
        for chunk, source, score in rows
    ]