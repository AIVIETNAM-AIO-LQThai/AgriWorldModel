import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from agriworldmodel.db.base import Base

class AssertionEvidence(Base):
    __tablename__ = "assertion_evidence"

    __table_args__ = (
        UniqueConstraint(
            "assertion_id",
            "source_id",
            "locator",
            name="uq_assertion_evidence_locator",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    assertion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agronomic_assertion.id"), nullable=False, index=True
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_source.id"), nullable=False, index=True
    )

    # Examples:
    # "p. 12"
    # "Section 4.2"
    # "Label - Directions for Use"
    locator: Mapped[str] = mapped_column(
        String(500), nullable=False
    )

    support_note: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )