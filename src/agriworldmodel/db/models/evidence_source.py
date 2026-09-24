import uuid
from typing import Any

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agriworldmodel.db.base import Base

class EvidenceSource(Base):
    __tablename__ = "evidence_source"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(500), nullable=False
    )

    publisher: Mapped[str | None] = mapped_column(
        String(300), nullable=True
    )

    published_year: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    url: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    language: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    jurisdiction: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )