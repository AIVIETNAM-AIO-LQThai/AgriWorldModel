from typing import Annotated, Literal
from pydantic import BaseModel, Field

PositiveFloat = Annotated[float, Field(gt=0)]
Percent = Annotated[float, Field(ge=0, le=100)]

class FertilizerApplicationPayload(BaseModel):
    product_name: str

    amount: PositiveFloat
    amount_unit: Literal["kg", "g", "L", "mL"]

    basis: Literal["total", "per_tree", "per_ha"]

    n_pct: Percent | None = None
    p2o5_pct: Percent | None = None
    k2o_pct: Percent | None = None

    method: str | None = None
    notes: str | None = None

class PesticideApplicationPayload(BaseModel):
    product_name: str

    active_ingredients: list[str] = Field(
        default_factory=list
    )

    target: str | None = None

    dose_value: PositiveFloat | None = None
    dose_unit: str | None = None

    method: str | None = None
    notes: str | None = None

def validate_event_payload(
    event_type: str, payload: dict
) -> dict:
    if event_type == "fertilizer_application":
        return FertilizerApplicationPayload.model_validate(payload).model_dump()

    if event_type == "pesticide_application":
        return PesticideApplicationPayload.model_validate(payload).model_dump()

    return payload