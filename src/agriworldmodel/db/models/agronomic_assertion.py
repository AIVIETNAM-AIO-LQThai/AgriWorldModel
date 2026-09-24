import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from agriworldmodel.db.base import Base

class AgronomicAssertion(Base):
    __tablename__ = "agronomic_assertion"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    assertion_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )

    subject: Mapped[str] = mapped_column(
        String(300), nullable=False
    )

    predicate: Mapped[str] = mapped_column(
        String(200), nullable=False
    )

    object_text: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    direction: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )

    condition_text: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    crop: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )