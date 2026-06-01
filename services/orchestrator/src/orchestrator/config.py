"""Configuration for the orchestrator service."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Azure OpenAI
    aoai_endpoint: str = "https://localhost"
    aoai_key: str = ""
    aoai_api_version: str = "2024-08-01-preview"
    aoai_draft_model: str = "gpt-4o-mini"   # fast + cheap for drafting/extraction/coding
    aoai_review_model: str = "gpt-4o"       # supervisor + critic

    # Cosmos DB (Phase 3) — optional; no-ops when blank
    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database: str = "clinicalscribe"

    # MCP server URLs (Phase 2) — defaults point to local dev servers
    mcp_medical_kb_url: str = "http://localhost:8010"
    mcp_coding_url: str = "http://localhost:8011"
    mcp_ehr_url: str = "http://localhost:8012"
    mcp_drug_url: str = "http://localhost:8013"

    # Service
    environment: str = "local"
    log_level: str = "INFO"
    port: int = 8001


settings = Settings()
