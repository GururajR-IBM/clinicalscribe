"""Configuration for the ingestion-worker service."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Postgres (encounter state)
    database_url: str = "postgresql://postgres:postgres@localhost:5432/clinicalscribe"

    # Azure Blob Storage — audio download
    azure_storage_connection_string: str = ""
    azure_storage_container_encounter_media: str = "encounter-media"

    # Azure OpenAI — Whisper transcription (phase 1 uses AOAI Whisper)
    aoai_endpoint: str = "https://localhost"
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
