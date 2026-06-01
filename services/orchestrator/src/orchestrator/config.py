"""Configuration for the orchestrator service.

Bring-your-own LLM: set AOAI_ENDPOINT + AOAI_KEY to any Azure OpenAI account.
When these are blank, all agents return safe stub data so the service still boots
in local dev. The orchestrator never provisions an AOAI resource of its own.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # -- BYO Azure OpenAI (any account / subscription) ----------------------
    aoai_endpoint: str = ""                       # blank -> stub mode
    aoai_key: str = ""
    aoai_api_version: str = "2024-08-01-preview"
    aoai_draft_model: str = "gpt-4o-mini"        # cheap draft + extraction + coding
    aoai_review_model: str = "gpt-4o-mini"       # default to mini for cost; override to gpt-4o for prod
    aoai_embedding_model: str = "text-embedding-3-small"  # 1536 dims, ~5x cheaper than 3-large

    # -- Cosmos DB (optional; no-ops when blank) ----------------------------
    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database: str = "clinicalscribe"

    # -- MCP server URLs ----------------------------------------------------
    mcp_medical_kb_url: str = "http://localhost:8010"
    mcp_coding_url: str = "http://localhost:8011"
    mcp_ehr_url: str = "http://localhost:8012"
    mcp_drug_url: str = "http://localhost:8013"

    # -- Service ------------------------------------------------------------
    environment: str = "local"
    log_level: str = "INFO"
    port: int = 8001


settings = Settings()
