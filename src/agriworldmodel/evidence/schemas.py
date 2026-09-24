import enum
import uuid
from typing import Any

from pydantic import BaseModel, Field, model_validator

class EvidenceSourceType(str, enum.Enum):
    LITERATURE = "literature"
    REGULATION = "regulation"
    PRODUCT_LABEL = "product_label"
    EXTENSION_GUIDE = "extension_guide"
    EXPERT_REVIEW = "expert_review"

class AssertionType(str, enum.Enum):
    RELATION = "relation"
    DIRECTIONAL_EFFECT = "directional_effect"
    CONSTRAINT = "constraint"
    REQUIREMENT = "requirement"

class EffectDirection(str, enum.Enum):
    INCREASE = "increase"
    DECREASE = "decrease"

class EvidenceSourceCreate(BaseModel):
    source_type: EvidenceSourceType

    title: str = Field(min_length=1)

    publisher: str | None = None
    published_year: int | None = None
    url: str | None = None
    language: str | None = None
    jurisdiction: str | None = None

    source_metadata: dict[str, Any] = Field(
        default_factory=dict
    )

class AgronomicAssertionCreate(BaseModel):
    assertion_type: AssertionType

    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object_text: str = Field(min_length=1)

    direction: EffectDirection | None = None

    condition_text: str | None = None
    crop: str | None = None

    @model_validator(mode="after")
    def validate_direction(self):
        if (
            self.assertion_type == AssertionType.DIRECTIONAL_EFFECT
            and self.direction is None
        ):
            raise ValueError("Directional-effect assertions require direction.")

        if (
            self.assertion_type != AssertionType.DIRECTIONAL_EFFECT
            and self.direction is not None
        ):
            raise ValueError("Only directional-effect assertions may have direction.")

        return self

class EvidenceSupportCreate(BaseModel):
    source_id: uuid.UUID
    locator: str = Field(min_length=1)
    support_note: str | None = None