from typing import Literal

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://"
        "agriworld:agriworld_dev"
        "@localhost:5432/agriworld"
    )

    # ---------------------------------------------------------------
    # LLM
    # ---------------------------------------------------------------
    llm_provider: Literal["lmstudio"] = "lmstudio"

    lmstudio_base_url: str = "http://127.0.0.1:1234/v1"
    lmstudio_model: str = "qwen/qwen3-30b-a3b-2507"
    # LM Studio does not require this placeholder unless
    # authentication is enabled, but the OpenAI client expects
    # an API-key value.
    lmstudio_api_key: str = "lm-studio"

    # Keep generation conservative for research reproducibility.
    lmstudio_temperature: float = 0.1
    lmstudio_max_tokens: int = 1200
    lmstudio_seed: int = 42

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()