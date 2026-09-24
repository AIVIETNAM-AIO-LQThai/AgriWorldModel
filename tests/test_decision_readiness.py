import datetime

from agriworldmodel.db.models.crop_cycle import CropCycle
from agriworldmodel.db.models.farm import Farm, ManagementUnit
from agriworldmodel.decisions.readiness import prepare_decision_readiness
from agriworldmodel.decisions.registry import DecisionRequirementCreate, register_decision_requirement
from agriworldmodel.decisions.schemas import DecisionType
from agriworldmodel.evidence.schemas import (
    AgronomicAssertionCreate, AssertionType,
    EvidenceSourceCreate, EvidenceSourceType, EvidenceSupportCreate,
)
from agriworldmodel.evidence.service import register_evidence_source, register_supported_assertion

UTC = datetime.timezone.utc

def dt(day: int) -> datetime.datetime:
    return datetime.datetime(2026, 9, day, 8, 0, tzinfo=UTC,)

def make_crop_cycle(
    db_session, *, crop="durian", cultivar=None,
):
    farm = Farm(
        name="Readiness Fixture Farm", province="Dong Nai",
    )

    unit = ManagementUnit(
        farm=farm,
        name="Block B3",
        area_m2=10_000,
    )

    db_session.add(farm)
    db_session.flush()

    cycle = CropCycle(management_unit_id=unit.id, crop=crop, cultivar=cultivar)

    db_session.add(cycle)
    db_session.flush()

    return unit, cycle

def make_requirement(db_session, *, crop="durian"):
    source = register_evidence_source(
        db_session,
        EvidenceSourceCreate(
            source_type=EvidenceSourceType.LITERATURE,
            title="Synthetic Readiness Source",
            publisher="Fixture Publisher",
            published_year=2026,
        ),
    )

    assertion = register_supported_assertion(
        db_session,
        assertion=AgronomicAssertionCreate(
            assertion_type=AssertionType.REQUIREMENT,
            subject="fixture N1 decision",
            predicate="requires",
            object_text="cultivar information",
            crop=crop,
        ),
        supports=[
            EvidenceSupportCreate(
                source_id=source.id,
                locator="p. 42",
            )
        ],
    )

    register_decision_requirement(
        db_session,
        DecisionRequirementCreate(
            assertion_id=assertion.id,
            decision_type=DecisionType.NUTRIENT,
            field_path="cultivar",
            description="Fixture cultivar requirement.",
        ),
    )

    return source, assertion

# -------------------------------------------------------------------
# 1. Missing required data produces a not-ready packet with provenance.
# -------------------------------------------------------------------
def test_not_ready_packet_contains_provenance(db_session):
    unit, cycle = make_crop_cycle(db_session, cultivar=None)

    source, assertion = make_requirement(db_session)

    packet = prepare_decision_readiness(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
    )

    assert packet.missing_data.ready is False
    assert len(packet.missing_data.missing_required) == 1

    missing = packet.missing_data.missing_required[0]

    assert missing.field_path == "cultivar"
    assert missing.assertion_id == assertion.id

    assert len(packet.requirement_provenance) == 1

    provenance = packet.requirement_provenance[0]

    assert provenance.assertion_id == assertion.id
    assert len(provenance.citations) == 1

    citation = provenance.citations[0]

    assert citation.source_id == source.id
    assert citation.locator == "p. 42"

# -------------------------------------------------------------------
# 2. Present required data produces a ready packet.
#
# Provenance is retained even when the requirement is satisfied,
# because the rule still needs to remain auditable.
# -------------------------------------------------------------------
def test_ready_packet_retains_requirement_provenance(db_session):
    unit, cycle = make_crop_cycle(db_session, cultivar="Ri6")

    _, assertion = make_requirement(db_session)

    packet = prepare_decision_readiness(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
    )

    assert packet.missing_data.ready is True
    assert packet.missing_data.missing_required == []
    assert len(packet.requirement_provenance) == 1
    assert packet.requirement_provenance[0].assertion_id == assertion.id

# -------------------------------------------------------------------
# 3. Requirements for another crop must not enter the packet.
# -------------------------------------------------------------------
def test_readiness_packet_respects_crop_scope(db_session):
    unit, cycle = make_crop_cycle(
        db_session,
        crop="rice",
        cultivar=None,
    )

    make_requirement(db_session, crop="durian")

    packet = prepare_decision_readiness(
        db_session,
        decision_type=DecisionType.NUTRIENT,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=dt(15),
        knowledge_cutoff=dt(15),
    )

    assert packet.requirements == []
    assert packet.missing_data.ready is True
    assert packet.requirement_provenance == []