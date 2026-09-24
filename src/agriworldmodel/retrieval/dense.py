import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from agriworldmodel.db.models.evidence_source import EvidenceSource
from agriworldmodel.db.models.knowledge_chunk import KnowledgeChunk
from agriworldmodel.retrieval.embedding import DenseEmbedder, EMBEDDING_DIMENSION
from agriworldmodel.retrieval.schemas import RetrievedChunk

class DenseRetrievalError(ValueError):
    pass

def _validate_embedding(embedding: list[float]) -> None:
    if len(embedding) != EMBEDDING_DIMENSION:
        raise DenseRetrievalError(
            "Dense embedding must have "
            f"{EMBEDDING_DIMENSION} dimensions; "
            f"received {len(embedding)}."
        )

def store_chunk_embedding(
    session: Session, *,
    chunk_id: uuid.UUID,
    embedding: list[float],
    model_name: str,
) -> KnowledgeChunk:
    """
    Persist a validated dense embedding for one chunk.
    """
    _validate_embedding(embedding)

    chunk = session.get(KnowledgeChunk, chunk_id,)

    if chunk is None:
        raise DenseRetrievalError("Knowledge chunk does not exist.")

    chunk.embedding = embedding
    chunk.embedding_model = model_name

    session.flush()

    return chunk

def embed_chunk(
    session: Session, *,
    chunk_id: uuid.UUID,
    embedder: DenseEmbedder,
) -> KnowledgeChunk:
    """
    Compute and store one chunk embedding.
    """
    chunk = session.get(KnowledgeChunk, chunk_id,)

    if chunk is None:
        raise DenseRetrievalError("Knowledge chunk does not exist.")

    embedding = embedder.embed_documents([chunk.content])[0]

    return store_chunk_embedding(
        session,
        chunk_id=chunk.id,
        embedding=embedding,
        model_name=embedder.model_name,
    )

def search_dense_chunks(
    session: Session, *,
    query_embedding: list[float],
    crop: str | None = None,
    limit: int = 10,
    embedding_model: str | None = None,
) -> list[RetrievedChunk]:
    """
    Retrieve chunks using cosine similarity.

    Only chunks with stored dense embeddings participate.
    """
    _validate_embedding(query_embedding)

    distance = (
        KnowledgeChunk.embedding.cosine_distance(query_embedding)
    ).label("distance")

    stmt = (
        select(
            KnowledgeChunk, EvidenceSource, distance,
        )
        .join(
            EvidenceSource,
            KnowledgeChunk.source_id == EvidenceSource.id,
        )
        .where(KnowledgeChunk.embedding.is_not(None))
    )

    if crop is not None:
        stmt = stmt.where(
            or_(
                KnowledgeChunk.crop.is_(None),
                func.lower(KnowledgeChunk.crop) == crop.lower(),
            )
        )

    if embedding_model is not None:
        stmt = stmt.where(KnowledgeChunk.embedding_model == embedding_model)

    stmt = (
        stmt
        .order_by(
            distance.asc(),
            KnowledgeChunk.id.asc(),
        )
        .limit(limit)
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

            # cosine_distance:
            # 0 = identical
            # larger = less similar
            score=1.0 - float(distance_value),
        )
        for chunk, source, distance_value in rows
    ]


def search_dense_text(
    session: Session, *,
    query_text: str,
    embedder: DenseEmbedder,
    crop: str | None = None,
    limit: int = 10,
) -> list[RetrievedChunk]:
    """
    Convenience boundary:
    text query -> embedding -> pgvector search.
    """
    if not query_text.strip():
        return []

    query_embedding = embedder.embed_query(query_text)

    return search_dense_chunks(
        session,
        query_embedding=query_embedding,
        crop=crop,
        limit=limit,
        embedding_model=embedder.model_name,
    )