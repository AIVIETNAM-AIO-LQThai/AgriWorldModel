import datetime

import pytest

from agriworldmodel.db.models.crop_cycle import CropCycle
from agriworldmodel.db.models.event import Event
from agriworldmodel.db.models.farm import Farm, ManagementUnit
from agriworldmodel.decisions.context import build_decision_context
from agriworldmodel.decisions.requirements import (
    RequirementDefinitionError, RequirementSpec, evaluate_requirements
)
from agriworldmodel.decisions.schemas import DecisionType

UTC = datetime.timezone.utc

def dt(day: int) -> datetime.datetime:
    return datetime.datetime(2026, 9, day, 8, 0, tzinfo=UTC,)

def make_context(db_session, *, cultivar="Ri6"):
    farm = Farm(name="Requirement Fixture Farm", province="Dong Nai")

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
        cultivar=cultivar,
    )

    db_session.add(cycle)
    db_session.flush()

    context = build_decision_context(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
    )

    return context

# -------------------------------------------------------------------
# 1. A required field that is present should satisfy the requirement.
# -------------------------------------------------------------------
def test_present_required_field_is_satisfied(db_session):
    context = make_context(db_session, cultivar="Ri6")

    requirements = [
        RequirementSpec(
            id="fixture-cultivar",
            decision_type=DecisionType.NUTRIENT,
            field_path="cultivar",
            description="Fixture requirement for cultivar.",
        )
    ]

    report = evaluate_requirements(context, requirements)

    assert report.ready is True
    assert report.missing_required == []
    assert report.checked_requirements == ["fixture-cultivar"]

# -------------------------------------------------------------------
# 2. Missing required information must block decision readiness.
# -------------------------------------------------------------------
def test_missing_required_field_blocks_readiness(db_session):
    context = make_context(db_session, cultivar=None)

    requirements = [
        RequirementSpec(
            id="fixture-cultivar",
            decision_type=DecisionType.NUTRIENT,
            field_path="cultivar",
            description=(
                "Fixture requirement for cultivar."
            ),
        )
    ]

    report = evaluate_requirements(context, requirements)

    assert report.ready is False
    assert len(report.missing_required) == 1
    assert report.missing_required[0].field_path == "cultivar"

# -------------------------------------------------------------------
# 3. Missing optional information must not block readiness.
# -------------------------------------------------------------------
def test_missing_optional_field_does_not_block(db_session):
    context = make_context(db_session, cultivar=None)

    requirements = [
        RequirementSpec(
            id="fixture-optional-cultivar",
            decision_type=DecisionType.NUTRIENT,
            field_path="cultivar",
            description=(
                "Fixture optional requirement."
            ),
            required=False,
        )
    ]

    report = evaluate_requirements(context, requirements)

    assert report.ready is True
    assert report.missing_required == []
    assert len(report.missing_optional) == 1

# -------------------------------------------------------------------
# 4. An invalid requirement path is a configuration error,
#    not missing farm data.
# -------------------------------------------------------------------
def test_invalid_requirement_path_is_rejected(db_session):
    context = make_context(db_session)

    requirements = [
        RequirementSpec(
            id="broken-fixture",
            decision_type=DecisionType.NUTRIENT,

            # This field does not exist.
            field_path="nutrient_state.magic_field",

            description="Broken fixture.",
        )
    ]

    with pytest.raises(RequirementDefinitionError):
        evaluate_requirements(context, requirements)