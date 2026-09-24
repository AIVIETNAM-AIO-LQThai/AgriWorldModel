import datetime

import pytest
from sqlalchemy import select

from agriworldmodel.db.models.crop_cycle import CropCycle
from agriworldmodel.db.models.event import Event
from agriworldmodel.db.models.farm import Farm, ManagementUnit
from agriworldmodel.events.schemas import EventProposal
from agriworldmodel.events.service import commit_confirmed_event, propose_event
from agriworldmodel.events.validation import EventValidationError

UTC = datetime.timezone.utc

def dt(day: int) -> datetime.datetime:
    return datetime.datetime(2026, 9, day, 8, 0, tzinfo=UTC)

def make_two_units(db_session):
    """
    Create one farm with two management units.

    We use two units to test that events/crop cycles cannot
    accidentally cross farm-block boundaries.
    """
    farm = Farm(
        name="Fixture Farm",
        province="Dong Nai",
    )

    unit_a = ManagementUnit(
        farm=farm,
        name="Block A",
        area_m2=10_000,
    )

    unit_b = ManagementUnit(
        farm=farm,
        name="Block B",
        area_m2=8_000,
    )

    db_session.add(farm)
    db_session.flush()

    return unit_a, unit_b


# -------------------------------------------------------------------
# 1. A valid fertilizer proposal should be accepted.
# -------------------------------------------------------------------
def test_valid_fertilizer_proposal_succeeds(db_session):
    unit_a, _ = make_two_units(db_session)

    proposal = EventProposal(
        management_unit_id=unit_a.id,
        event_type="fertilizer_application",
        occurred_start=dt(10),
        source="farmer_confirmed",
        payload={
            "product_name": "NPK 16-16-8",
            "amount": 2.0,
            "amount_unit": "kg",
            "basis": "per_tree",
        },
    )

    validated = propose_event(db_session, proposal)

    assert validated.event_type == "fertilizer_application"
    assert validated.normalized_payload["product_name"] == "NPK 16-16-8"
    assert validated.normalized_payload["amount"] == 2.0

    # propose_event must NOT write anything to the ledger.
    events = list(db_session.scalars(select(Event)))

    assert len(events) == 0


# -------------------------------------------------------------------
# 2. Invalid fertilizer data should be rejected.
# -------------------------------------------------------------------
def test_malformed_fertilizer_payload_is_rejected(db_session):
    unit_a, _ = make_two_units(db_session)

    proposal = EventProposal(
        management_unit_id=unit_a.id,
        event_type="fertilizer_application",
        occurred_start=dt(10),
        source="farmer_confirmed",
        payload={
            "product_name": "NPK 16-16-8",

            # Invalid: amount must be > 0.
            "amount": -2.0,
            "amount_unit": "kg",
            "basis": "per_tree",
        },
    )

    with pytest.raises(EventValidationError):
        propose_event(db_session, proposal)


# -------------------------------------------------------------------
# 3. Unknown event types should be rejected.
# -------------------------------------------------------------------
def test_unknown_event_type_is_rejected(db_session):
    unit_a, _ = make_two_units(db_session)

    proposal = EventProposal(
        management_unit_id=unit_a.id,

        # AgriWorldModel doesn't support this event.
        event_type="magic_fertilizer_event",

        occurred_start=dt(10),
        source="farmer_confirmed",

        payload={
            "whatever": "value",
        },
    )

    with pytest.raises(EventValidationError):
        propose_event(db_session, proposal)


# -------------------------------------------------------------------
# 4. Crop cycle must belong to the same management unit.
# -------------------------------------------------------------------
def test_crop_cycle_from_another_unit_is_rejected(db_session):
    unit_a, unit_b = make_two_units(db_session)

    # This crop cycle belongs to Block B.
    cycle_b = CropCycle(
        management_unit_id=unit_b.id,
        crop="durian",
        cultivar="Monthong",
    )

    db_session.add(cycle_b)
    db_session.flush()

    # But this proposal says the event belongs to Block A.
    proposal = EventProposal(
        management_unit_id=unit_a.id,
        crop_cycle_id=cycle_b.id,
        event_type="fertilizer_application",
        occurred_start=dt(10),
        source="farmer_confirmed",
        payload={
            "product_name": "NPK 16-16-8",
            "amount": 2.0,
            "amount_unit": "kg",
            "basis": "per_tree",
        },
    )

    with pytest.raises(EventValidationError):
        propose_event(db_session, proposal)


# -------------------------------------------------------------------
# 5. An event from another management unit cannot be superseded.
# -------------------------------------------------------------------
def test_superseding_event_from_another_unit_is_rejected(db_session):
    unit_a, unit_b = make_two_units(db_session)

    # First create a legitimate event for Block B.
    original_proposal = EventProposal(
        management_unit_id=unit_b.id,
        event_type="fertilizer_application",
        occurred_start=dt(10),
        source="farmer_confirmed",
        payload={
            "product_name": "NPK 16-16-8",
            "amount": 2.0,
            "amount_unit": "kg",
            "basis": "per_tree",
        },
    )

    original_validated = propose_event(
        db_session, original_proposal
    )

    original_event = commit_confirmed_event(
        db_session, original_validated, confirmed=True
    )

    # Now Block A attempts to "correct" Block B's event.
    correction = EventProposal(
        management_unit_id=unit_a.id,
        event_type="fertilizer_application",
        occurred_start=dt(10),
        source="farmer_correction",
        payload={
            "product_name": "NPK 16-16-8",
            "amount": 1.5,
            "amount_unit": "kg",
            "basis": "per_tree",
        },
        supersedes_id=original_event.id,
    )

    with pytest.raises(EventValidationError):
        propose_event(
            db_session, correction
        )


# -------------------------------------------------------------------
# 6. An unconfirmed proposal must NOT enter the ledger.
# -------------------------------------------------------------------
def test_unconfirmed_proposal_cannot_enter_database(db_session):
    unit_a, _ = make_two_units(db_session)

    proposal = EventProposal(
        management_unit_id=unit_a.id,
        event_type="fertilizer_application",
        occurred_start=dt(10),
        source="farmer_confirmed",
        payload={
            "product_name": "NPK 16-16-8",
            "amount": 2.0,
            "amount_unit": "kg",
            "basis": "per_tree",
        },
    )

    validated = propose_event(db_session, proposal)

    with pytest.raises(ValueError):
        commit_confirmed_event(
            db_session, validated, confirmed=False
        )

    events = list(db_session.scalars(select(Event)))

    assert len(events) == 0


# -------------------------------------------------------------------
# 7. A confirmed proposal SHOULD enter the ledger.
# -------------------------------------------------------------------
def test_confirmed_proposal_enters_database(db_session):
    unit_a, _ = make_two_units(db_session)

    proposal = EventProposal(
        management_unit_id=unit_a.id,
        event_type="fertilizer_application",
        occurred_start=dt(10),
        source="farmer_confirmed",
        payload={
            "product_name": "NPK 16-16-8",
            "amount": 2.0,
            "amount_unit": "kg",
            "basis": "per_tree",
        },
    )

    validated = propose_event(db_session, proposal)

    event = commit_confirmed_event(
        db_session, validated, confirmed=True
    )

    saved_event = db_session.get(Event, event.id)

    assert saved_event is not None
    assert saved_event.event_type == "fertilizer_application"
    assert saved_event.payload["product_name"] == "NPK 16-16-8"
    assert saved_event.payload["amount"] == 2.0

# -------------------------------------------------------------------
# 8. recorded_at must be assigned by AgriWorldModel itself.
# -------------------------------------------------------------------
def test_recorded_at_is_assigned_by_system(db_session):
    unit_a, _ = make_two_units(db_session)

    proposal = EventProposal(
        management_unit_id=unit_a.id,
        event_type="fertilizer_application",

        # Event actually happened Sep 10.
        occurred_start=dt(10),
        source="farmer_confirmed",
        payload={
            "product_name": "NPK 16-16-8",
            "amount": 2.0,
            "amount_unit": "kg",
            "basis": "per_tree",
        },
    )

    validated = propose_event(db_session, proposal)

    before_commit = datetime.datetime.now(UTC)

    event = commit_confirmed_event(
        db_session,
        validated,
        confirmed=True,
    )

    after_commit = datetime.datetime.now(UTC)

    assert event.recorded_at is not None
    assert before_commit <= event.recorded_at <= after_commit

    # Important:
    # when the event happened and when the system learned it
    # are two different concepts.
    assert event.occurred_start == dt(10)
    assert event.recorded_at != event.occurred_start