import datetime
import uuid

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, aliased

from agriworldmodel.db.models.event import Event
from agriworldmodel.state.schemas import FarmStateSnapshot, StateEvent

def get_visible_events(
    session: Session, *,
    management_unit_id: uuid.UUID,
    effective_at: datetime.datetime,
    knowledge_cutoff: datetime.datetime,
    crop_cycle_id: uuid.UUID | None = None
) -> list[Event]:
    """
    Return events that:

    1. had occurred by effective_at;
    2. had been recorded by knowledge_cutoff;
    3. had not already been superseded by information known
       by knowledge_cutoff.

    This prevents hindsight leakage during retrospective evaluation.
    """
    superseding_event = aliased(Event)

    has_known_superseder = exists().where(
        superseding_event.supersedes_id == Event.id,
        superseding_event.management_unit_id == Event.management_unit_id,
        superseding_event.recorded_at <= knowledge_cutoff
    )

    conditions = [
        Event.management_unit_id == management_unit_id,
        Event.occurred_start <= effective_at,
        Event.recorded_at <= knowledge_cutoff,
        ~has_known_superseder
    ]

    if crop_cycle_id is not None:
        conditions.append(Event.crop_cycle_id == crop_cycle_id)

    stmt = select(Event).where(
        Event.management_unit_id == management_unit_id,
        Event.occurred_start <= effective_at,
        Event.recorded_at <= knowledge_cutoff,
        ~has_known_superseder,
    ).order_by(
        Event.occurred_start.asc(),
        Event.recorded_at.asc()
    )

    return list(session.scalars(stmt))

def get_state(
    session: Session, *,
    management_unit_id: uuid.UUID,
    effective_at: datetime.datetime,
    knowledge_cutoff: datetime.datetime,
    crop_cycle_id: uuid.UUID | None = None
) -> FarmStateSnapshot:
    events = get_visible_events(
        session,
        management_unit_id=management_unit_id,
        effective_at=effective_at,
        knowledge_cutoff=knowledge_cutoff,
        crop_cycle_id=crop_cycle_id
    )

    return FarmStateSnapshot(
        management_unit_id=management_unit_id,
        crop_cycle_id=crop_cycle_id,
        effective_at=effective_at,
        knowledge_cutoff=knowledge_cutoff,
        events=[StateEvent.model_validate(event) for event in events]
    )