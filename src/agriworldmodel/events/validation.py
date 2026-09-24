from sqlalchemy.orm import Session

from agriworldmodel.db.models.crop_cycle import CropCycle
from agriworldmodel.db.models.event import Event
from agriworldmodel.domain.events import validate_event_payload
from agriworldmodel.events.schemas import (
    EventProposal,
    ValidatedEventProposal,
)

class EventValidationError(ValueError):
    pass

def validate_event_proposal(
    session: Session,
    proposal: EventProposal,
) -> ValidatedEventProposal:
    # 1. Validate event-specific payload.
    try:
        normalized_payload = validate_event_payload(
            proposal.event_type,
            proposal.payload,
        )
    except Exception as exc:
        raise EventValidationError(
            f"Invalid {proposal.event_type} payload: {exc}"
        ) from exc

    # 2. Crop cycle must belong to the same management unit.
    if proposal.crop_cycle_id is not None:
        cycle = session.get(CropCycle, proposal.crop_cycle_id)
        if cycle is None:
            raise EventValidationError("Crop cycle does not exist.")
        if cycle.management_unit_id != proposal.management_unit_id:
            raise EventValidationError("Crop cycle belongs to another management unit.")

    # 3. Validate correction target.
    if proposal.supersedes_id is not None:
        old_event = session.get(Event, proposal.supersedes_id)
        if old_event is None:
            raise EventValidationError("Superseded event does not exist.")
        if old_event.management_unit_id != proposal.management_unit_id:
            raise EventValidationError(
                "Cannot supersede an event from another management unit."
            )
        if old_event.event_type != proposal.event_type:
            raise EventValidationError("Correction must preserve event type.")

    return ValidatedEventProposal(
        **proposal.model_dump(),
        normalized_payload=normalized_payload,
    )