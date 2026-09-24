import uuid
from typing import Any

from pydantic import BaseModel, AwareDatetime


class EventProposal(BaseModel):
    management_unit_id: uuid.UUID
    crop_cycle_id: uuid.UUID | None = None

    event_type: str

    occurred_start: AwareDatetime
    occurred_end: AwareDatetime | None = None

    source: str
    payload: dict[str, Any]

    supersedes_id: uuid.UUID | None = None


class ValidatedEventProposal(EventProposal):
    normalized_payload: dict[str, Any]