"""Configuration for the ingestion-worker service.

Bring-your-own LLM: AOAI_ENDPOINT + AOAI_KEY point at any Azure OpenAI account
(Whisper deployment). Blank values disable transcription and the worker falls
back to passing through any pre-supplied transcript on the encounter row.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Local DB (compliance-friendly: SQLite file, no infra, no network surface).
    # Override with a Postgres URL only if you provision the postgres module.
    database_url: str = "sqlite:///./clinicalscribe.db"

    # Azure Blob Storage -- audio download
    azure_storage_connection_string: str = ""
    azure_storage_container_encounter_media: str = "encounter-media"

    # BYO Azure OpenAI -- Whisper transcription
    aoai_endpoint: str = ""
    aoai_key: str = ""
    aoai_whisper_deployment: str = "whisper"

    # Orchestrator internal endpoint
    orchestrator_base_url: str = "http://orchestrator:8001"
    orchestrator_timeout_seconds: float = 300.0

    # Worker settings
    poll_interval_seconds: float = 5.0
    max_audio_bytes: int = 25 * 1024 * 1024  # 25 MB (Azure OpenAI Whisper limit)
    environment: str = "local"
    log_level: str = "INFO"


settings = Settings()
