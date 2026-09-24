import datetime
import uuid

from sqlalchemy.orm import Session

from agriworldmodel.db.models.crop_cycle import CropCycle
from agriworldmodel.db.models.farm import Farm, ManagementUnit
from agriworldmodel.decisions.schemas import DecisionContext, DecisionType
from agriworldmodel.state.derived import derive_crop_protection_state, derive_nutrient_state
from agriworldmodel.state.service import get_state

class DecisionContextError(ValueError):
    pass

def build_decision_context(
    session: Session,
    *,
    decision_type: DecisionType,
    management_unit_id: uuid.UUID,
    crop_cycle_id: uuid.UUID,
    effective_at: datetime.datetime,
    knowledge_cutoff: datetime.datetime,
) -> DecisionContext:
    """
    Assemble the deterministic farm context available for a
    particular agricultural decision.

    No LLM or retrieval occurs here.
    """

    unit = session.get(
        ManagementUnit,
        management_unit_id,
    )

    if unit is None:
        raise DecisionContextError("Management unit does not exist.")

    cycle = session.get(CropCycle, crop_cycle_id)

    if cycle is None:
        raise DecisionContextError("Crop cycle does not exist.")
    if cycle.management_unit_id != unit.id:
        raise DecisionContextError(
            "Crop cycle does not belong to the requested management unit."
        )

    farm = session.get(Farm, unit.farm_id)

    if farm is None:
        raise DecisionContextError("Farm does not exist.")

    farm_state = get_state(
        session,
        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,
        effective_at=effective_at,
        knowledge_cutoff=knowledge_cutoff,
    )

    nutrient_state = None
    crop_protection_state = None

    if decision_type == DecisionType.NUTRIENT:
        nutrient_state = derive_nutrient_state(farm_state)

    elif decision_type == DecisionType.CROP_PROTECTION:
        crop_protection_state = (
            derive_crop_protection_state(farm_state))

    else:
        raise DecisionContextError(
            f"Unsupported decision type: {decision_type}"
        )

    return DecisionContext(
        decision_type=decision_type,

        management_unit_id=unit.id,
        crop_cycle_id=cycle.id,

        effective_at=effective_at,
        knowledge_cutoff=knowledge_cutoff,

        farm_name=farm.name,
        management_unit_name=unit.name,

        crop=cycle.crop,
        cultivar=cycle.cultivar,

        farm_state=farm_state,

        nutrient_state=nutrient_state,
        crop_protection_state=crop_protection_state,
    )