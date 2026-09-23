import datetime
import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict

class StateEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    management_unit_id: uuid.UUID
    crop_cycle_id: uuid.UUID | None

    event_type: str

    occurred_start: datetime.datetime
    occurred_end: datetime.datetime | None
    recorded_at: datetime.datetime

    source: str
    payload: dict[str, Any]

    supersedes_id: uuid.UUID | None

class FarmStateSnapshot(BaseModel):
    management_unit_id: uuid.UUID
    crop_cycle_id: uuid.UUID | None = None

    # What point in farm history are we reconstructing?
    effective_at: datetime.datetime

    # What info was the system allowed to know?
    knowledge_cutoff: datetime.datetime

    events: list[StateEvent]