"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Clerk
    clerk_jwks_url: str = "https://clerk.your-domain.com/.well-known/jwks.json"
    clerk_issuer: str = "https://clerk.your-domain.com"

    # Local DB (gateway currently uses an in-memory store; this URL is reserved
    # for the future asyncpg-backed store. Default = SQLite for laptop dev.)
    database_url: str = "sqlite:///./clinicalscribe.db"

    # Azure Blob Storage
    azure_storage_account_name: str = ""
    azure_storage_container_encounter_media: str = "encounter-media"
    azure_storage_connection_string: str = ""  # local dev only; use managed identity in prod

    # Service metadata
    environment: str = "local"
    log_level: str = "INFO"


settings = Settings()
