import datetime

from sqlalchemy.orm import Session

from agriworldmodel.db.models.event import Event
from agriworldmodel.events.schemas import (
    EventProposal,
    ValidatedEventProposal,
)
from agriworldmodel.events.validation import (
    validate_event_proposal,
)


UTC = datetime.timezone.utc


def propose_event(
    session: Session,
    proposal: EventProposal,
) -> ValidatedEventProposal:
    """
    Validate and normalize an event proposal.

    This does NOT write anything to the ledger.
    """
    return validate_event_proposal(
        session,
        proposal,
    )


def commit_confirmed_event(
    session: Session,
    proposal: ValidatedEventProposal,
    *,
    confirmed: bool,
) -> Event:
    """
    Only confirmed proposals may enter the event ledger.
    """

    if not confirmed:
        raise ValueError(
            "Event must be explicitly confirmed before commit."
        )

    event = Event(
        management_unit_id=proposal.management_unit_id,
        crop_cycle_id=proposal.crop_cycle_id,
        event_type=proposal.event_type,
        occurred_start=proposal.occurred_start,
        occurred_end=proposal.occurred_end,

        # System-controlled knowledge timestamp.
        recorded_at=datetime.datetime.now(UTC),

        source=proposal.source,
        payload=proposal.normalized_payload,
        supersedes_id=proposal.supersedes_id,
    )

    session.add(event)
    session.flush()

    return event