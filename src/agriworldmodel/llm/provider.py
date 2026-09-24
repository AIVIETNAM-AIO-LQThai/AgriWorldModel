from typing import Any, Protocol

class LLMProvider(Protocol):
    """
    Vendor-neutral structured-generation boundary.

    Concrete providers may use OpenAI, Anthropic, a local model,
    or another backend. Decision logic must not depend on the
    vendor implementation.
    """
    model_name: str
    def generate_json(
        self, *, system_prompt: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        ...