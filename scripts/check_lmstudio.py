from pydantic import BaseModel

from agriworldmodel.config import settings
from agriworldmodel.llm.factory import (
    build_llm_provider,
)


class SmokeResponse(BaseModel):
    status: str
    value: int


provider = build_llm_provider()

print("Provider:", type(provider).__name__)
print("Model:", provider.model_name)

result = provider.generate_json(
    system_prompt=(
        "Return exactly the requested structured output."
    ),
    payload={
        "instruction": (
            "Set status to 'ok' and value to 42."
        )
    },
    response_model=SmokeResponse,
)

print(result)