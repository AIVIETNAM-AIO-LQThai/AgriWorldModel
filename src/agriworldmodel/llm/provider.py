from typing import Any, Protocol

from pydantic import BaseModel

class LLMProvider(Protocol):
    """
    Vendor-neutral structured-generation boundary.
    """
    model_name: str
    def generate_json(
        self, *,
        system_prompt: str,
        payload: dict[str, Any],
        response_model: type[BaseModel],
    ) -> dict[str, Any]:
        ...