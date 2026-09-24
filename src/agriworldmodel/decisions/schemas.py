import enum
import uuid

from pydantic import AwareDatetime, BaseModel

from agriworldmodel.state.derived import CropProtectionState, NutrientState
from agriworldmodel.state.schemas import FarmStateSnapshot

class DecisionType(str, enum.Enum):
    NUTRIENT = "N1"
    CROP_PROTECTION = "P1"

class DecisionContext(BaseModel):
    decision_type: DecisionType

    management_unit_id: uuid.UUID
    crop_cycle_id: uuid.UUID

    effective_at: AwareDatetime
    knowledge_cutoff: AwareDatetime

    farm_name: str
    management_unit_name: str

    crop: str
    cultivar: str | None

    area_m2: float | None
    tree_count: int | None

    farm_state: FarmStateSnapshot

    nutrient_state: NutrientState | None = None
    crop_protection_state: CropProtectionState | None = None