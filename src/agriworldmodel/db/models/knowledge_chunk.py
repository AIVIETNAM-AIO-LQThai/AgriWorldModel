import uuid
from typing import Any

from pgvector.sqlalchemy import Vector

from sqlalchemy import Computed, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agriworldmodel.db.base import Base

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunk"

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "chunk_index",
            name="uq_knowledge_chunk_source_index"
        ),
        Index(
            "ix_knowledge_chunk_search_vector",
            "search_vector",
            postgresql_using="gin"
        )
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_source.id"), nullable=False, index=True
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)
     # Dense semantic representation.
    #
    # BGE-M3 produces 1024-dimensional dense embeddings.
    # Nullable so lexical-only ingestion remains valid.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1024), nullable=True
    )
    embedding_model: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )

    # Exact location inside the original source.
    # Examples:
    # "p. 12"
    # "pp. 12-13"
    # "Section 4.2"
    locator: Mapped[str] = mapped_column(String(500), nullable=False)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # None = globally applicable.
    crop: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # PostgreSQL-native lexical representation.
    #
    # We deliberately use "simple" rather than English stemming
    # because the corpus will eventually contain Vietnamese.
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector("
            "'simple'::regconfig, "
            "coalesce(content, '')"
            ")",
            persisted=True,
        ),
        nullable=False,
    )