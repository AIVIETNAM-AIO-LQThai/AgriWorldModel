import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from agriworldmodel.llm.openai_provider import OpenAIProvider, OpenAIProviderError

class FixtureResponse(BaseModel):
    answer: str

class FakeResponses:
    def __init__(self, parsed):
        self.parsed = parsed
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)

        return SimpleNamespace(
            output_parsed=self.parsed
        )

class FakeClient:
    def __init__(self, parsed):
        self.responses = FakeResponses(parsed)

# -------------------------------------------------------------------
# 1. OpenAI adapter should use Responses structured parsing.
# -------------------------------------------------------------------
def test_openai_provider_uses_structured_responses():
    client = FakeClient(FixtureResponse(answer="fixture"))

    provider = OpenAIProvider(client=client)

    result = provider.generate_json(
        system_prompt="Fixture system prompt.",
        payload={
            "crop": "durian",
            "value": 40.0,
        },
        response_model=FixtureResponse,
    )

    assert result == {
        "answer": "fixture"
    }

    call = client.responses.calls[0]

    assert call["model"] == "gpt-5.6-sol"
    assert call["text_format"] is FixtureResponse
    assert call["reasoning"] == {
        "effort": "medium"
    }

# -------------------------------------------------------------------
# 2. The reasoning packet should be serialized into the user input.
# -------------------------------------------------------------------
def test_openai_provider_serializes_payload():
    client = FakeClient(FixtureResponse(answer="fixture"))

    provider = OpenAIProvider(client=client)

    provider.generate_json(
        system_prompt="System.",
        payload={
            "crop": "durian",
            "n_kg_total": 40.0,
        },
        response_model=FixtureResponse,
    )

    call = client.responses.calls[0]

    assert call["input"][0] == {
        "role": "system",
        "content": "System.",
    }

    user_payload = json.loads(
        call["input"][1]["content"]
    )

    assert user_payload["crop"] == "durian"
    assert user_payload["n_kg_total"] == 40.0

# -------------------------------------------------------------------
# 3. Model and reasoning effort should remain configurable.
# -------------------------------------------------------------------
def test_openai_provider_accepts_model_configuration():
    client = FakeClient(FixtureResponse(answer="fixture"))

    provider = OpenAIProvider(
        model_name="fixture-model",
        reasoning_effort="high",
        client=client,
    )

    provider.generate_json(
        system_prompt="System.",
        payload={},
        response_model=FixtureResponse,
    )

    call = client.responses.calls[0]

    assert call["model"] == "fixture-model"
    assert call["reasoning"] == {
        "effort": "high"
    }

# -------------------------------------------------------------------
# 4. Missing structured output must not silently pass through.
# -------------------------------------------------------------------
def test_openai_provider_rejects_missing_parsed_output():
    client = FakeClient(None)

    provider = OpenAIProvider(client=client)

    with pytest.raises(OpenAIProviderError):
        provider.generate_json(
            system_prompt="System.",
            payload={},
            response_model=FixtureResponse,
        )