"""Eval runner configuration.

Bring-your-own LLM: AOAI_ENDPOINT + AOAI_KEY may point at any Azure OpenAI
account. When blank, the rubric returns stub scores (CI-safe).
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # BYO AOAI (judge model). Default to gpt-4o-mini to minimize cost; bump to
    # gpt-4o for production-grade scoring once live runs are needed.
    aoai_endpoint: str = ""
    aoai_key: str = ""
    aoai_api_version: str = "2024-08-01-preview"
    aoai_judge_model: str = "gpt-4o-mini"

    # Orchestrator endpoint -- used for live batch eval
    orchestrator_url: str = "http://localhost:8001"
    orchestrator_timeout: float = 120.0

    # Cosmos DB -- read agent_runs and traces for trending (optional)
    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database: str = "clinicalscribe"

    # Output
    output_dir: str = "eval_results"


settings = Settings()
