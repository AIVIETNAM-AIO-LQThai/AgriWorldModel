import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from agriworldmodel.llm.lmstudio_provider import LMStudioProvider, LMStudioProviderError

class FixtureResponse(BaseModel):
    answer: str

class FakeCompletions:
    def __init__(self, content: str):
        self.content = content
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content)
                )
            ]
        )


class FakeChat:
    def __init__(self, content: str):
        self.completions = FakeCompletions(content)

class FakeClient:
    def __init__(self, content: str):
        self.chat = FakeChat(content)

def test_lmstudio_provider_returns_structured_json():
    client = FakeClient(
        json.dumps(
            {
                "answer": "fixture"
            }
        )
    )

    provider = LMStudioProvider(
        model_name="agriworld-qwen",
        base_url="http://localhost:1234/v1",
        client=client,
    )

    result = provider.generate_json(
        system_prompt="System.",
        payload={"crop": "durian"},
        response_model=FixtureResponse,
    )

    assert result == {
        "answer": "fixture"
    }

def test_lmstudio_provider_uses_local_model_configuration():
    client = FakeClient('{"answer":"fixture"}')

    provider = LMStudioProvider(
        model_name="agriworld-qwen",
        base_url="http://localhost:1234/v1",
        temperature=0.1,
        max_tokens=1200,
        seed=42,
        client=client,
    )

    provider.generate_json(
        system_prompt="System.",
        payload={},
        response_model=FixtureResponse,
    )

    call = client.chat.completions.calls[0]

    assert call["model"] == "agriworld-qwen"
    assert call["temperature"] == 0.1
    assert call["max_tokens"] == 1200
    assert call["seed"] == 42

def test_lmstudio_provider_sends_json_schema():
    client = FakeClient('{"answer":"fixture"}')

    provider = LMStudioProvider(
        model_name="agriworld-qwen",
        base_url="http://localhost:1234/v1",
        client=client,
    )

    provider.generate_json(
        system_prompt="System.",
        payload={},
        response_model=FixtureResponse,
    )

    call = client.chat.completions.calls[0]

    response_format = call["response_format"]

    assert (
        response_format["type"] == "json_schema"
    )

    assert (
        response_format["json_schema"]["schema"]["properties"]["answer"]["type"] == "string"
    )

def test_lmstudio_provider_rejects_invalid_output():
    client = FakeClient('{"wrong_field":"fixture"}')

    provider = LMStudioProvider(
        model_name="agriworld-qwen",
        base_url="http://localhost:1234/v1",
        client=client,
    )

    with pytest.raises(LMStudioProviderError):
        provider.generate_json(
            system_prompt="System.",
            payload={},
            response_model=FixtureResponse,
        )