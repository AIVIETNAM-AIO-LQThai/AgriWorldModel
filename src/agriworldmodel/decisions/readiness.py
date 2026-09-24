import datetime
import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from agriworldmodel.decisions.context import build_decision_context
from agriworldmodel.decisions.registry import load_requirement_specs
from agriworldmodel.decisions.requirements import MissingDataReport, RequirementSpec, evaluate_requirements
from agriworldmodel.decisions.schemas import DecisionContext, DecisionType
from agriworldmodel.evidence.query import AssertionProvenance, get_assertion_provenance

class DecisionReadinessPacket(BaseModel):
    context: DecisionContext
    requirements: list[RequirementSpec]
    missing_data: MissingDataReport
    requirement_provenance: list[AssertionProvenance]


def prepare_decision_readiness(
    session: Session, *,
    decision_type: DecisionType,
    management_unit_id: uuid.UUID,
    crop_cycle_id: uuid.UUID,
    effective_at: datetime.datetime,
    knowledge_cutoff: datetime.datetime
) -> DecisionReadinessPacket:
    """
    Assemble the deterministic pre-reasoning packet for one
    agricultural decision.

    No LLM or retrieval is performed here.
    """
    context = build_decision_context(
        session,
        decision_type=decision_type,
        management_unit_id=management_unit_id,
        crop_cycle_id=crop_cycle_id,
        effective_at=effective_at,
        knowledge_cutoff=knowledge_cutoff,
    )

    requirements = load_requirement_specs(session, context=context)

    missing_data = evaluate_requirements(context, requirements)
    assertion_ids = []

    for requirement in requirements:
        if (
            requirement.assertion_id is not None
            and requirement.assertion_id not in assertion_ids
        ):
            assertion_ids.append(requirement.assertion_id)

    provenance = [
        get_assertion_provenance(session, assertion_id)
        for assertion_id in assertion_ids
    ]

    return DecisionReadinessPacket(
        context=context,
        requirements=requirements,
        missing_data=missing_data,
        requirement_provenance=provenance,
    )