from agriworldmodel.db.models.event import Event
from agriworldmodel.state.derived import derive_nutrient_state, derive_crop_protection_state
from agriworldmodel.state.service import get_state

from tests.test_state import dt, make_unit

def test_nutrient_state_uses_visible_events_only(db_session):
    unit = make_unit(db_session)

    db_session.add(
        Event(
            management_unit_id=unit.id,
            event_type="fertilizer_application",
            occurred_start=dt(10),
            recorded_at=dt(13),
            source="farmer_confirmed",
            payload={
                "product_name": "Fixture NPK",
                "amount": 2.0,
                "amount_unit": "kg",
                "basis": "per_tree",
            },
        )
    )

    db_session.flush()

    before_known = get_state(
        db_session,
        management_unit_id=unit.id,
        effective_at=dt(11),
        knowledge_cutoff=dt(11),
    )

    nutrient_before = derive_nutrient_state(before_known)

    assert nutrient_before.application_count == 0
    assert nutrient_before.last_application is None

    after_known = get_state(
        db_session,
        management_unit_id=unit.id,
        effective_at=dt(14),
        knowledge_cutoff=dt(14),
    )

    nutrient_after = derive_nutrient_state(after_known)

    assert nutrient_after.application_count == 1
    assert nutrient_after.last_application is not None
    assert nutrient_after.last_application.product_name == "Fixture NPK"
    assert nutrient_after.last_application.days_since == 4

def test_crop_protection_state_tracks_active_ingredients(db_session):
    unit = make_unit(db_session)
    db_session.add_all(
        [
            Event(
                management_unit_id=unit.id,
                event_type="pesticide_application",
                occurred_start=dt(8),
                recorded_at=dt(8),
                source="farm_record",
                payload={
                    "product_name": "Product A",
                    "active_ingredients": ["metalaxyl"],
                },
            ),
            Event(
                management_unit_id=unit.id,
                event_type="pesticide_application",
                occurred_start=dt(12),
                recorded_at=dt(12),
                source="farm_record",
                payload={
                    "product_name": "Product B",
                    "active_ingredients": ["azoxystrobin"],
                },
            ),
        ]
    )

    db_session.flush()

    snapshot = get_state(
        db_session,
        management_unit_id=unit.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
    )

    protection = derive_crop_protection_state(snapshot)

    assert protection.application_count == 2
    assert protection.last_application.product_name == "Product B"
    assert protection.last_application.days_since == 3
    assert protection.active_ingredient_history == [
        "metalaxyl", "azoxystrobin",
    ]