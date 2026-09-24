from typing import Any

from pydantic import BaseModel

from agriworldmodel.decisions.schemas import DecisionContext, DecisionType

class RequirementDefinitionError(ValueError):
    pass

class RequirementSpec(BaseModel):
    """
    Defines one piece of information that a decision may require.

    Actual agronomic requirements will later be backed by
    literature, regulations, labels, or expert review.
    """
    id: str
    decision_type: DecisionType
    field_path: str
    description: str
    required: bool = True
    source_ref: str | None = None

class MissingDataItem(BaseModel):
    requirement_id: str
    field_path: str
    description: str
    required: bool

class MissingDataReport(BaseModel):
    decision_type: DecisionType
    ready: bool
    checked_requirements: list[str]
    missing_required: list[MissingDataItem]
    missing_optional: list[MissingDataItem]


def _resolve_field_path(
    obj: Any, field_path: str
) -> Any:
    """
    Resolve a dotted field path such as:

        nutrient_state.last_application.product_name

    against a Pydantic model or dictionary.
    """
    current = obj

    for part in field_path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            if part not in current:
                raise RequirementDefinitionError(f"Unknown field path: {field_path}")

            current = current[part]

        else:
            if not hasattr(current, part):
                raise RequirementDefinitionError(f"Unknown field path: {field_path}")

            current = getattr(current, part)

    return current


def _is_missing(value: Any) -> bool:
    """
    Define what counts as missing.

    Zero and False are legitimate values and therefore
    must NOT be treated as missing.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def evaluate_requirements(
    context: DecisionContext, requirements: list[RequirementSpec]
) -> MissingDataReport:
    """
    Evaluate requirements applicable to this decision context.

    This function does not make agronomic judgments.
    It only checks whether explicitly declared information
    requirements are satisfied.
    """
    applicable = [
        requirement
        for requirement in requirements
        if requirement.decision_type == context.decision_type
    ]

    missing_required: list[MissingDataItem] = []
    missing_optional: list[MissingDataItem] = []

    for requirement in applicable:
        value = _resolve_field_path(context, requirement.field_path)

        if not _is_missing(value):
            continue

        item = MissingDataItem(
            requirement_id=requirement.id,
            field_path=requirement.field_path,
            description=requirement.description,
            required=requirement.required,
        )

        if requirement.required:
            missing_required.append(item)
        else:
            missing_optional.append(item)

    return MissingDataReport(
        decision_type=context.decision_type,

        ready=len(missing_required) == 0,

        checked_requirements=[requirement.id for requirement in applicable],

        missing_required=missing_required,
        missing_optional=missing_optional,
    )