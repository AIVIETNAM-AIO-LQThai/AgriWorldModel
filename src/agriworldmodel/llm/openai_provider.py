import json
from typing import Any, Literal

from pydantic import BaseModel

DEFAULT_OPENAI_MODEL = "gpt-5.6-sol"

ReasoningEffort = Literal["none", "low", "medium", "high", "xhigh", "max"]

class OpenAIProviderError(RuntimeError):
    pass

class OpenAIProvider:
    """
    Structured-output OpenAI adapter.

    Decision and agricultural logic must remain outside this
    class. This adapter only converts our vendor-neutral provider
    contract into an OpenAI Responses API request.
    """
    def __init__(
        self, *,
        model_name: str = DEFAULT_OPENAI_MODEL,
        reasoning_effort: ReasoningEffort = "medium",
        client: Any | None = None,
    ):
        self.model_name = model_name
        self.reasoning_effort = reasoning_effort

        if client is None:
            from openai import OpenAI
            client = OpenAI()

        self._client = client

    def generate_json(
        self, *, system_prompt: str,
        payload: dict[str, Any],
        response_model: type[BaseModel],
    ) -> dict[str, Any]:
        payload_json = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )

        response = self._client.responses.parse(
            model=self.model_name,

            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": payload_json,
                },
            ],

            text_format=response_model,

            reasoning={
                "effort": self.reasoning_effort,
            },
        )

        parsed = response.output_parsed

        if parsed is None:
            raise OpenAIProviderError("OpenAI returned no parsed structured output.")

        if not isinstance(parsed, BaseModel):
            raise OpenAIProviderError("OpenAI returned an unexpected parsed output type.")

        return parsed.model_dump(mode="json")