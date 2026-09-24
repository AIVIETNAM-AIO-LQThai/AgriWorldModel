from sqlalchemy import select
from sqlalchemy.orm import Session

from agriworldmodel.db.models.evidence_source import EvidenceSource
from agriworldmodel.db.models.knowledge_chunk import KnowledgeChunk
from agriworldmodel.retrieval.schemas import KnowledgeChunkCreate

class RetrievalIngestionError(ValueError):
    pass

def register_knowledge_chunk(
    session: Session, chunk: KnowledgeChunkCreate,
) -> KnowledgeChunk:
    """
    Persist one already-created source chunk.

    Actual PDF/text chunking will be implemented separately.
    """
    source = session.get(EvidenceSource, chunk.source_id,)

    if source is None:
        raise RetrievalIngestionError("Evidence source does not exist.")

    existing = session.scalar(
        select(KnowledgeChunk).where(
            KnowledgeChunk.source_id == chunk.source_id,
            KnowledgeChunk.chunk_index == chunk.chunk_index,
        )
    )

    if existing is not None:
        raise RetrievalIngestionError("Chunk index already exists for this source.")

    db_chunk = KnowledgeChunk(
        source_id=chunk.source_id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        locator=chunk.locator,
        language=chunk.language,
        crop=chunk.crop,
        chunk_metadata=chunk.chunk_metadata,
    )

    session.add(db_chunk)
    session.flush()

    return db_chunk