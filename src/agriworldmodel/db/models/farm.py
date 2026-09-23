import uuid

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agriworldmodel.db.base import Base

class Farm(Base):
    __tablename__ = "farm"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String(200))
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)

    management_units: Mapped[list["ManagementUnit"]] = relationship(
        back_populates="farm", cascade="all, delete-orphan"
    )

class ManagementUnit(Base):
    __tablename__ = "management_unit"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farm.id"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(200))
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)

    farm: Mapped["Farm"] = relationship(back_populates="management_units")