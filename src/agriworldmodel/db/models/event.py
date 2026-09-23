import datetime
import uuid
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agriworldmodel.db.base import Base

class Event(Base):
    __tablename__ = "event"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    management_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("management_unit.id"), nullable=False, index=True
    )

    crop_cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("crop_cycle.id"), nullable=True, index=True
    )

    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    # When the event happen on the farm.
    occurred_start: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    occurred_end: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # When AgriWorldModel learned about it.
    recorded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    
    source: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )

    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("event.id"), nullable=True
    )