import datetime

import pytest

from agriworldmodel.db.models.crop_cycle import CropCycle
from agriworldmodel.db.models.event import Event
from agriworldmodel.db.models.farm import Farm, ManagementUnit
from agriworldmodel.decisions.context import DecisionContextError, build_decision_context
from agriworldmodel.decisions.schemas import DecisionType

UTC = datetime.timezone.utc

def dt(day: int) -> datetime.datetime:
    return datetime.datetime(2026, 9, day, 8, 0, tzinfo=UTC)

def make_crop_cycle(db_session):
    farm = Farm(
        name="Decision Fixture Farm",
        province="Dong Nai",
    )

    unit = ManagementUnit(
        farm=farm,
        name="Block B3",
        area_m2=10_000,
    )

    db_session.add(farm)
    db_session.flush()

    cycle = CropCycle(
        management_unit_id=unit.id,
        crop="durian",
        cultivar="Ri6",
        tree_count=180,
    )

    db_session.add(cycle)
    db_session.flush()

    return farm, unit, cycle

# -------------------------------------------------------------------
# 1. N1 context contains farm identity and derived nutrient state.
# -------------------------------------------------------------------
def test_build_nutrient_decision_context(db_session):
    farm, unit, cycle = make_crop_cycle(db_session)

    db_session.add(
        Event(
            management_unit_id=unit.id,
            crop_cycle_id=cycle.id,
            event_type="fertilizer_application",
            occurred_start=dt(10),
            recorded_at=dt(10),
            source="farm_record",
            payload={
                "product_name": "NPK 16-16-8",
                "amount": 2.0,
                "amount_unit": "kg",
                "basis": "per_tree",
            },
        )
    )

    db_session.flush()

    context = build_decision_context(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
    )

    assert context.decision_type == DecisionType.NUTRIENT
    assert context.farm_name == farm.name
    assert context.management_unit_name == unit.name
    assert context.crop == "durian"
    assert context.cultivar == "Ri6"
    assert context.area_m2 == 10_000
    assert context.tree_count == 180
    assert context.nutrient_state is not None
    assert context.nutrient_state.application_count == 1
    assert context.nutrient_state.last_application.product_name == "NPK 16-16-8"
    assert context.crop_protection_state is None

# -------------------------------------------------------------------
# 2. P1 context contains derived crop-protection state.
# -------------------------------------------------------------------
def test_build_crop_protection_decision_context(db_session):
    _, unit, cycle = make_crop_cycle(db_session)

    db_session.add(
        Event(
            management_unit_id=unit.id,
            crop_cycle_id=cycle.id,
            event_type="pesticide_application",
            occurred_start=dt(12),
            recorded_at=dt(12),
            source="farm_record",
            payload={
                "product_name": "Product A",
                "active_ingredients": ["metalaxyl"],
            },
        )
    )

    db_session.flush()

    context = build_decision_context(
        db_session,
        decision_type=DecisionType.CROP_PROTECTION,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
    )

    assert context.crop_protection_state is not None
    assert context.crop_protection_state.application_count == 1
    assert context.crop_protection_state.active_ingredient_history == ["metalaxyl"]
    assert context.nutrient_state is None

# -------------------------------------------------------------------
# 3. A decision cannot use a crop cycle from another block.
# -------------------------------------------------------------------
def test_decision_context_rejects_wrong_unit_cycle(db_session):
    farm = Farm(name="Fixture Farm", province="Dong Nai")

    unit_a = ManagementUnit(farm=farm, name="Block A")

    unit_b = ManagementUnit(farm=farm, name="Block B")

    db_session.add(farm)
    db_session.flush()

    cycle_b = CropCycle(
        management_unit_id=unit_b.id,
        crop="durian",
    )

    db_session.add(cycle_b)
    db_session.flush()

    with pytest.raises(DecisionContextError):
        build_decision_context(
            db_session,
            decision_type=DecisionType.NUTRIENT,
            management_unit_id=unit_a.id,
            crop_cycle_id=cycle_b.id,
            effective_at=dt(15),
            knowledge_cutoff=dt(15),
        )

# -------------------------------------------------------------------
# 4. Decision context must respect the historical knowledge cutoff.
#
# A late-reported farm event must not leak into a decision that was
# made before AgriWorldModel learned about that event.
# -------------------------------------------------------------------
def test_decision_context_prevents_hindsight_leakage(db_session):
    _, unit, cycle = make_crop_cycle(db_session)

    db_session.add(
        Event(
            management_unit_id=unit.id,
            crop_cycle_id=cycle.id,
            event_type="fertilizer_application",

            # Actually happened Sep 10.
            occurred_start=dt(10),

            # Only reported Sep 13.
            recorded_at=dt(13),
            source="farmer_confirmed",
            payload={
                "product_name": "NPK 16-16-8",
                "amount": 2.0,
                "amount_unit": "kg",
                "basis": "per_tree",
            },
        )
    )

    db_session.flush()

    context = build_decision_context(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,

        # Decision made Sep 11.
        effective_at=dt(11),
        knowledge_cutoff=dt(11),
    )

    assert context.nutrient_state is not None
    assert context.nutrient_state.application_count == 0
    assert context.nutrient_state.last_application is None