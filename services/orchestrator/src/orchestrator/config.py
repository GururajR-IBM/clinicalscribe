"""Configuration for the orchestrator service."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Azure OpenAI
    aoai_endpoint: str = "https://localhost"
    aoai_key: str = ""
    aoai_api_version: str = "2024-08-01-preview"
    aoai_draft_model: str = "gpt-4o-mini"   # fast + cheap for drafting
    aoai_review_model: str = "gpt-4o"       # higher quality for critic pass

    # Service
    environment: str = "local"
    log_level: str = "INFO"
    port: int = 8001


settings = Settings()
