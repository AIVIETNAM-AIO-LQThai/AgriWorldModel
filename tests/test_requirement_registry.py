import datetime
import uuid

import pytest

from agriworldmodel.db.models.crop_cycle import CropCycle
from agriworldmodel.db.models.farm import Farm, ManagementUnit
from agriworldmodel.decisions.context import build_decision_context
from agriworldmodel.decisions.registry import (
    DecisionRequirementCreate, DecisionRequirementError,
    load_requirement_specs, register_decision_requirement
)
from agriworldmodel.decisions.requirements import evaluate_requirements
from agriworldmodel.decisions.schemas import DecisionType
from agriworldmodel.evidence.schemas import (
    AgronomicAssertionCreate, AssertionType,
    EvidenceSourceCreate, EvidenceSourceType, EvidenceSupportCreate
)
from agriworldmodel.evidence.service import register_evidence_source, register_supported_assertion

UTC = datetime.timezone.utc

def dt(day: int) -> datetime.datetime:
    return datetime.datetime(2026, 9, day, 8, 0, tzinfo=UTC,)

def make_context(
    db_session, *, crop="durian", cultivar=None,
):
    farm = Farm(
        name="Requirement Registry Fixture Farm", province="Dong Nai",
    )

    unit = ManagementUnit(
        farm=farm,
        name="Block B3",
        area_m2=10_000,
    )

    db_session.add(farm)
    db_session.flush()

    cycle = CropCycle(
        management_unit_id=unit.id, crop=crop, cultivar=cultivar,
    )

    db_session.add(cycle)
    db_session.flush()

    return build_decision_context(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
    )

def make_supported_assertion(
    db_session, *,
    assertion_type=AssertionType.REQUIREMENT,
    crop="durian"
):
    source = register_evidence_source(
        db_session,
        EvidenceSourceCreate(
            source_type=EvidenceSourceType.LITERATURE,
            title="Synthetic Requirement Fixture",
            publisher="Fixture Publisher",
            published_year=2026,
        ),
    )

    assertion = register_supported_assertion(
        db_session,
        assertion=AgronomicAssertionCreate(
            assertion_type=assertion_type,
            subject="fixture N1 decision",
            predicate="requires",
            object_text="fixture cultivar information",
            crop=crop,
        ),
        supports=[
            EvidenceSupportCreate(source_id=source.id, locator="p. 10")
        ]
    )

    return assertion

# -------------------------------------------------------------------
# 1. A decision requirement cannot reference a missing assertion.
# -------------------------------------------------------------------
def test_missing_assertion_is_rejected(db_session):
    with pytest.raises(DecisionRequirementError):
        register_decision_requirement(
            db_session,
            DecisionRequirementCreate(
                assertion_id=uuid.uuid4(),
                decision_type=DecisionType.NUTRIENT,
                field_path="cultivar",
                description="Fixture cultivar requirement.",
            ),
        )

# -------------------------------------------------------------------
# 2. Only REQUIREMENT assertions may justify decision requirements.
# -------------------------------------------------------------------
def test_non_requirement_assertion_is_rejected(db_session):
    assertion = make_supported_assertion(
        db_session,
        assertion_type=AssertionType.RELATION,
    )

    with pytest.raises(DecisionRequirementError):
        register_decision_requirement(
            db_session,
            DecisionRequirementCreate(
                assertion_id=assertion.id,
                decision_type=(
                    DecisionType.NUTRIENT
                ),
                field_path="cultivar",
                description="Fixture cultivar requirement.",
            ),
        )

# -------------------------------------------------------------------
# 3. Evidence-backed requirements load into executable specs.
# -------------------------------------------------------------------
def test_load_evidence_backed_requirement(db_session):
    assertion = make_supported_assertion(db_session)

    register_decision_requirement(
        db_session,
        DecisionRequirementCreate(
            assertion_id=assertion.id,
            decision_type=DecisionType.NUTRIENT,
            field_path="cultivar",
            description="Fixture cultivar requirement."
        ),
    )

    context = make_context(db_session, cultivar="Ri6",)

    requirements = load_requirement_specs(db_session, context=context)

    assert len(requirements) == 1
    assert requirements[0].field_path == "cultivar"
    assert requirements[0].assertion_id == assertion.id

# -------------------------------------------------------------------
# 4. Missing-data results preserve the assertion provenance link.
# -------------------------------------------------------------------
def test_missing_data_preserves_assertion_id(db_session):
    assertion = make_supported_assertion(db_session)

    register_decision_requirement(
        db_session,
        DecisionRequirementCreate(
            assertion_id=assertion.id,
            decision_type=DecisionType.NUTRIENT,
            field_path="cultivar",
            description="Fixture cultivar requirement.",
        ),
    )

    context = make_context(db_session, cultivar=None,)
    requirements = load_requirement_specs(db_session, context=context)
    report = evaluate_requirements(context, requirements)

    assert report.ready is False
    assert len(report.missing_required) == 1
    
    missing = report.missing_required[0]

    assert missing.field_path == "cultivar"
    assert missing.assertion_id == assertion.id

# -------------------------------------------------------------------
# 5. Crop-specific requirements must not leak into another crop.
# -------------------------------------------------------------------
def test_requirement_is_scoped_to_crop(db_session):
    assertion = make_supported_assertion(
        db_session, crop="durian",
    )

    register_decision_requirement(
        db_session,
        DecisionRequirementCreate(
            assertion_id=assertion.id,
            decision_type=DecisionType.NUTRIENT,
            field_path="cultivar",
            description="Synthetic durian-only requirement.",
        ),
    )

    context = make_context(db_session, crop="rice", cultivar=None)

    requirements = load_requirement_specs(db_session, context=context)

    assert requirements == []