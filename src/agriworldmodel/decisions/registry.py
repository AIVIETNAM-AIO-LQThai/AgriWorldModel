import uuid

from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from agriworldmodel.db.models.agronomic_assertion import (
    AgronomicAssertion,
)
from agriworldmodel.db.models.decision_requirement import (
    DecisionRequirement,
)
from agriworldmodel.decisions.requirements import (
    RequirementSpec,
)
from agriworldmodel.decisions.schemas import (
    DecisionContext,
    DecisionType,
)


class DecisionRequirementError(ValueError):
    pass


class DecisionRequirementCreate(BaseModel):
    assertion_id: uuid.UUID

    decision_type: DecisionType

    field_path: str = Field(min_length=1)

    description: str = Field(min_length=1)

    required: bool = True


def register_decision_requirement(
    session: Session,
    requirement: DecisionRequirementCreate,
) -> DecisionRequirement:
    """
    Map one evidence-backed REQUIREMENT assertion onto a
    machine-readable DecisionContext field.
    """

    assertion = session.get(
        AgronomicAssertion,
        requirement.assertion_id,
    )

    if assertion is None:
        raise DecisionRequirementError(
            "Agronomic assertion does not exist."
        )

    if assertion.assertion_type != "requirement":
        raise DecisionRequirementError(
            "Decision requirements must be backed by "
            "a REQUIREMENT assertion."
        )

    db_requirement = DecisionRequirement(
        assertion_id=assertion.id,
        decision_type=requirement.decision_type.value,
        field_path=requirement.field_path,
        description=requirement.description,
        required=requirement.required,

        # Requirement automatically inherits crop scope
        # from its evidence-backed assertion.
        crop=assertion.crop,
    )

    session.add(db_requirement)
    session.flush()

    return db_requirement


def load_requirement_specs(
    session: Session,
    *,
    context: DecisionContext,
) -> list[RequirementSpec]:
    """
    Load requirement rules applicable to this decision.

    A requirement applies when:
    1. decision_type matches; and
    2. its crop is either global (None) or matches the
       current crop.
    """

    stmt = (
        select(DecisionRequirement)
        .where(
            DecisionRequirement.decision_type
            == context.decision_type.value,
            or_(
                DecisionRequirement.crop.is_(None),
                DecisionRequirement.crop
                == context.crop,
            ),
        )
        .order_by(
            DecisionRequirement.field_path.asc(),
            DecisionRequirement.id.asc(),
        )
    )

    rows = list(
        session.scalars(stmt)
    )

    return [
        RequirementSpec(
            id=str(row.id),
            decision_type=DecisionType(
                row.decision_type
            ),
            field_path=row.field_path,
            description=row.description,
            required=row.required,
            assertion_id=row.assertion_id,
        )
        for row in rows
    ]