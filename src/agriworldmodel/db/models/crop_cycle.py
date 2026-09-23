import datetime
import uuid

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from agriworldmodel.db.base import Base

class CropCycle(Base):
    __tablename__ = "crop_cycle"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    management_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("management_unit.id"), nullable=False
    )

    crop: Mapped[str] = mapped_column(String(100))
    cultivar: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    planted_on: Mapped[datetime.date | None] = mapped_column(
        Date, nullable=True
    )

    tree_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )