import uuid

from pydantic import BaseModel, Field


class DecisionRecommendation(BaseModel):
    """
    Structured model output for an N1 agricultural decision.

    References are identifiers into the deterministic reasoning
    packet rather than free-form citations invented by the model.
    """
    recommendation: str = Field(min_length=1)
    rationale: list[str] = Field(min_length=1)
    action_steps: list[str] = Field(default_factory=list)

    evidence_chunk_ids: list[uuid.UUID] = Field(min_length=1)
    calculated_fact_names: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)

class StructuredDecisionResult(BaseModel):
    model_name: str
    prompt_version: str
    recommendation: DecisionRecommendation