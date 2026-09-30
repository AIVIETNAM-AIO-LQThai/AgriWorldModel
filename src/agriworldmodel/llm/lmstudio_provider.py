import json
from typing import Any

from pydantic import BaseModel, ValidationError

class LMStudioProviderError(RuntimeError):
    pass

class LMStudioProvider:
    """
    Structured local-LLM provider backed by LM Studio.

    Uses LM Studio's OpenAI-compatible Chat Completions API.

    Agricultural reasoning, validation, and provenance logic
    remain outside this adapter.
    """
    def __init__(
        self, *, model_name: str,
        base_url: str,
        api_key: str = "lm-studio",
        temperature: float = 0.1,
        max_tokens: int = 1200,
        seed: int = 42,
        client: Any | None = None,
    ):
        self.model_name = model_name

        self.temperature = temperature
        self.max_tokens = max_tokens
        self.seed = seed

        if client is None:
            from openai import OpenAI

            client = OpenAI(base_url=base_url, api_key=api_key)

        self._client = client

    def generate_json(
        self, *,
        system_prompt: str,
        payload: dict[str, Any],
        response_model: type[BaseModel],
    ) -> dict[str, Any]:
        """
        Request grammar-constrained structured JSON from
        the local LM Studio model.
        """

        payload_json = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": response_model.__name__,
                "strict": True,
                "schema": response_model.model_json_schema(),
            },
        }

        response = (
            self._client
            .chat
            .completions
            .create(
                model=self.model_name,

                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": payload_json,
                    },
                ],

                response_format=response_format,

                temperature=self.temperature,
                max_tokens=self.max_tokens,
                seed=self.seed,

                stream=False,
            )
        )

        content = (
            response.choices[0].message.content
        )

        if not content:
            raise LMStudioProviderError("LM Studio returned no content.")

        try:
            raw = json.loads(content)
            parsed = response_model.model_validate(raw)

        except (json.JSONDecodeError, ValidationError) as exc:
            raise LMStudioProviderError("LM Studio returned invalid structured output.") from exc

        return parsed.model_dump(mode="json")