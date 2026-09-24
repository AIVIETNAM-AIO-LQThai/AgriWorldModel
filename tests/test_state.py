import datetime

from agriworldmodel.db.models.event import Event
from agriworldmodel.db.models.farm import Farm, ManagementUnit
from agriworldmodel.state.service import get_state
from agriworldmodel.db.models.crop_cycle import CropCycle

UTC = datetime.timezone.utc

def dt(day: int) -> datetime.datetime:
    return datetime.datetime(
        2026, 9, day, 8, 0, tzinfo=UTC
    )

def make_unit(db_session):
    farm = Farm(
        name="Fixture Farm",
        province="Dong Nai",
    )
    unit = ManagementUnit(
        farm=farm, name="Block B3", area_m2=10_000
    )

    db_session.add(farm)
    db_session.flush()

    return unit

def test_late_report_does_not_leak_into_past_state(db_session):
    unit = make_unit(db_session)

    event = Event(
        management_unit_id=unit.id,

        event_type="fertilizer_application",

        # Actually happened Sep 10.
        occurred_start=dt(10),

        # Agent only learned about it Sep 13.
        recorded_at=dt(13),

        source="farmer_confirmed",

        payload={
            "product": "NPK fixture",
            "kg_per_tree": 2.0,
        },
    )

    db_session.add(event)
    db_session.flush()

    # Agent makes a decision on Sep 11.
    state_sep11 = get_state(
        db_session,
        management_unit_id=unit.id,
        effective_at=dt(11),
        knowledge_cutoff=dt(11),
    )

    assert len(state_sep11.events) == 0

    # By Sep 14, the agent knows what happened.
    state_sep14 = get_state(
        db_session,
        management_unit_id=unit.id,
        effective_at=dt(14),
        knowledge_cutoff=dt(14),
    )

    assert len(state_sep14.events) == 1

    assert (
        state_sep14.events[0].event_type
        == "fertilizer_application"
    )

def test_correction_only_changes_state_after_it_is_known(db_session):
    unit = make_unit(db_session)

    original = Event(
        management_unit_id=unit.id,
        event_type="fertilizer_application",
        occurred_start=dt(10),
        recorded_at=dt(10),
        source="farmer_confirmed",
        payload={
            "product": "NPK fixture",
            "kg_per_tree": 2.0,
        },
    )

    db_session.add(original)
    db_session.flush()

    correction = Event(
        management_unit_id=unit.id,
        event_type="fertilizer_application",
        occurred_start=dt(10),

        # Correction only learned Sep 15.
        recorded_at=dt(15),

        source="farmer_correction",

        payload={
            "product": "NPK fixture",
            "kg_per_tree": 1.5,
        },

        supersedes_id=original.id,
    )

    db_session.add(correction)
    db_session.flush()

    # What did the system believe on Sep 12?
    state_before_correction = get_state(
        db_session,
        management_unit_id=unit.id,
        effective_at=dt(12),
        knowledge_cutoff=dt(12),
    )

    assert len(state_before_correction.events) == 1
    assert (
        state_before_correction.events[0]
        .payload["kg_per_tree"]
        == 2.0
    )

    # What does it believe after learning the correction?
    state_after_correction = get_state(
        db_session,
        management_unit_id=unit.id,
        effective_at=dt(16),
        knowledge_cutoff=dt(16),
    )

    assert len(state_after_correction.events) == 1
    assert (
        state_after_correction.events[0]
        .payload["kg_per_tree"]
        == 1.5
    )

def test_state_filters_events_by_crop_cycle(db_session):
    unit = make_unit(db_session)

    cycle_a = CropCycle(
        management_unit_id=unit.id,
        crop="durian",
        cultivar="Ri6",
    )

    cycle_b = CropCycle(
        management_unit_id=unit.id,
        crop="durian",
        cultivar="Monthong",
    )

    db_session.add_all([cycle_a, cycle_b])
    db_session.flush()

    event_a = Event(
        management_unit_id=unit.id,
        crop_cycle_id=cycle_a.id,
        event_type="fertilizer_application",
        occurred_start=dt(10),
        recorded_at=dt(10),
        source="farm_record",
        payload={
            "product_name": "NPK A",
            "amount": 2.0,
            "amount_unit": "kg",
            "basis": "per_tree",
        },
    )

    event_b = Event(
        management_unit_id=unit.id,
        crop_cycle_id=cycle_b.id,
        event_type="fertilizer_application",
        occurred_start=dt(11),
        recorded_at=dt(11),
        source="farm_record",
        payload={
            "product_name": "NPK B",
            "amount": 1.5,
            "amount_unit": "kg",
            "basis": "per_tree",
        },
    )

    db_session.add_all([event_a, event_b])
    db_session.flush()

    snapshot = get_state(
        db_session,
        management_unit_id=unit.id,
        crop_cycle_id=cycle_a.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
    )

    assert len(snapshot.events) == 1
    assert snapshot.events[0].crop_cycle_id == cycle_a.id
    assert snapshot.events[0].payload["product_name"] == "NPK A"