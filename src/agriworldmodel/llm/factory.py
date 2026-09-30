from agriworldmodel.config import (
    Settings,
    settings,
)
from agriworldmodel.llm.lmstudio_provider import (
    LMStudioProvider,
)
from agriworldmodel.llm.provider import (
    LLMProvider,
)


class LLMProviderConfigurationError(
    ValueError
):
    pass


def build_llm_provider(app_settings: Settings = settings) -> LLMProvider:
    if app_settings.llm_provider == "lmstudio":
        return LMStudioProvider(
            model_name=app_settings.lmstudio_model,
            base_url=app_settings.lmstudio_base_url,
            api_key=app_settings.lmstudio_api_key,
            temperature=app_settings.lmstudio_temperature,
            max_tokens=app_settings.lmstudio_max_tokens,
            seed=app_settings.lmstudio_seed,
        )

    raise LLMProviderConfigurationError(
        "Unsupported LLM provider: "
        f"{app_settings.llm_provider}"
    )