import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from agriworldmodel.db.base import Base

class DecisionRequirement(Base):
    __tablename__ = "decision_requirement"

    __table_args__ = (
        UniqueConstraint(
        "assertion_id", name="uq_decision_requirement_assertion"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # The evidence-backed REQUIREMENT assertion that justifies
    # why this decision input is needed.
    assertion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agronomic_assertion.id"), nullable=False, index=True
    )

    decision_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    # Path inside DecisionContext, for example:
    # "cultivar"
    # "nutrient_state.last_application"
    field_path: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Copied from AgronomicAssertion.crop when registered.
    # None means the requirement is crop-independent.
    crop: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )