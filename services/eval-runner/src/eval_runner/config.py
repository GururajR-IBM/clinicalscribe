"""Eval runner configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # AOAI — used for LLM-judge scoring (gpt-4o)
    # NOTE: Phase 5.1 + 5.3: use Opus 4.7 here for eval rubric generation and consequence review
    aoai_endpoint: str = "https://localhost"
    aoai_key: str = ""
    aoai_api_version: str = "2024-08-01-preview"
    aoai_judge_model: str = "gpt-4o"   # swap to claude-opus-4-7 via AOAI when available

    # Orchestrator endpoint — used for live batch eval
    orchestrator_url: str = "http://localhost:8001"
    orchestrator_timeout: float = 120.0

    # Cosmos DB — read agent_runs and traces for trending
    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database: str = "clinicalscribe"

    # Output
    output_dir: str = "eval_results"


settings = Settings()
