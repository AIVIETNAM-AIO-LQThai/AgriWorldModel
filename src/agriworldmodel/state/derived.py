import datetime
import uuid

from pydantic import BaseModel
from agriworldmodel.domain.events import (
    FertilizerApplicationPayload,
    PesticideApplicationPayload
)
from agriworldmodel.state.schemas import FarmStateSnapshot

class FertilizerApplicationState(BaseModel):
    event_id: uuid.UUID
    occurred_at: datetime.datetime
    days_since: int
    product_name: str
    amount: float
    amount_unit: str
    basis: str

class NutrientState(BaseModel):
    application_count: int
    last_application: FertilizerApplicationState | None

class PesticideApplicationState(BaseModel):
    event_id: uuid.UUID
    occurred_at: datetime.datetime
    days_since: int
    product_name: str
    active_ingredients: list[str]

class CropProtectionState(BaseModel):
    application_count: int
    last_application: PesticideApplicationState | None
    active_ingredient_history: list[str]

def _days_since(
    effective_at: datetime.datetime,
    occurred_at: datetime.datetime
) -> int:
    return max(0, (effective_at - occurred_at).days)

def derive_nutrient_state(snapshot: FarmStateSnapshot) -> NutrientState:
    applications = [
        event for event in snapshot.events
        if event.event_type == "fertilizer_application"
    ]

    if not applications:
        return NutrientState(application_count=0, last_application=None)

    latest = max(applications, key=lambda event: event.occurred_start)
    payload = FertilizerApplicationPayload.model_validate(latest.payload)

    return NutrientState(
        application_count=len(applications),
        last_application=FertilizerApplicationState(
            event_id=latest.id,
            occurred_at=latest.occurred_start,
            days_since=_days_since(
                snapshot.effective_at,
                latest.occurred_start
            ),
            product_name=payload.product_name,
            amount=payload.amount,
            amount_unit=payload.amount_unit,
            basis=payload.basis
        )
    )

def derive_crop_protection_state(snapshot: FarmStateSnapshot) -> CropProtectionState:
    applications = [
        event for event in snapshot.events
        if event.event_type == "pesticide_application"
    ]

    if not applications:
        return CropProtectionState(
            application_count=0,
            last_application=None,
            active_ingredient_history=[]
        )

    latest = max(applications, key=lambda event: event.occurred_start)
    latest_payload = PesticideApplicationPayload.model_validate(latest.payload)

    ingredient_history: list[str] = []

    for event in applications:
        payload = PesticideApplicationPayload.model_validate(event.payload)
        for ingredient in payload.active_ingredients:
            if ingredient not in ingredient_history:
                ingredient_history.append(ingredient)

    return CropProtectionState(
        application_count=len(applications),
        last_application=PesticideApplicationState(
            event_id=latest.id,
            occurred_at=latest.occurred_start,
            days_since=_days_since(
                snapshot.effective_at,
                latest.occurred_start
            ),
            product_name=latest_payload.product_name,
            active_ingredients=latest_payload.active_ingredients
        ),
        active_ingredient_history=ingredient_history
    )