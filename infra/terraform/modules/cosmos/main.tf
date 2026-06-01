# ── Cosmos DB NoSQL Account ────────────────────────────────────────────────
#
# Stores: agent_runs, evidence, embeddings, traces containers.
# (Relational data — users, encounters, codes, approvals — stays in Postgres.)
#
# Provisioned throughput: Autoscale at the database level so all containers share
# the 1 000–10 000 RU/s pool. Each container can override if needed.
#
# Geo-redundancy, multi-write: disabled for Phase 3 (Phase 6 adds failover).

resource "azurerm_cosmosdb_account" "main" {
  name                = "${var.name_prefix}-cosmos"
  location            = var.location
  resource_group_name = var.resource_group_name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"
  tags                = var.tags

  consistency_policy {
    consistency_level       = "Session"
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  # Disable public access — private endpoint added in Phase 6.
  # For Phase 3 lab dev, keep public access enabled with IP firewall.
  is_virtual_network_filter_enabled = false
  public_network_access_enabled     = true

  backup {
    type                = "Periodic"
    interval_in_minutes = 240
    retention_in_hours  = 24
    storage_redundancy  = "Local"
  }
}

# ── Database ───────────────────────────────────────────────────────────────

resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "clinicalscribe"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name

  autoscale_settings {
    max_throughput = 10000 # 1 000–10 000 RU/s autoscale shared across containers
  }
}

# ── Container: agent_runs ──────────────────────────────────────────────────
# Schema:
#   id            = run_id (UUID)
#   encounter_id  = partition key
#   agent_name    = "supervisor" | "entity_extraction" | "retrieval" | ...
#   started_at    = ISO-8601
#   completed_at  = ISO-8601 | null
#   input_tokens  = int
#   output_tokens = int
#   state_snapshot = embedded AgentState JSON
#   error         = null | string
# TTL: 90 days (compliance — audit logs must be retained)

resource "azurerm_cosmosdb_sql_container" "agent_runs" {
  name                = "agent_runs"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/encounter_id"]

  # Inherit autoscale from database — no per-container throughput
  # (omit throughput/autoscale_settings block to inherit)

  default_ttl = 90 * 24 * 60 * 60 # 90 days in seconds

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/state_snapshot/*" # Large embedded blob — exclude from index
    }
  }
}

# ── Container: evidence ────────────────────────────────────────────────────
# Schema:
#   id              = evidence_id (UUID)
#   encounter_id    = partition key
#   agent_run_id    = FK → agent_runs.id
#   source          = "ai_search" | "static_kb" | "ehr"
#   document_id     = string (AI Search doc key or KB term)
#   excerpt         = string
#   relevance_score = float
#   cited_in        = "subjective" | "objective" | "assessment" | "plan"
# TTL: 90 days (same as agent_runs)

resource "azurerm_cosmosdb_sql_container" "evidence" {
  name                = "evidence"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/encounter_id"]

  default_ttl = 90 * 24 * 60 * 60

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
  }
}

# ── Container: embeddings ──────────────────────────────────────────────────
# Stores Ada-002 embeddings for encounter transcripts + SOAP notes.
# Used by the Retrieval Agent for semantic similarity lookups.
#
# Schema:
#   id           = embedding_id (UUID)
#   encounter_id = partition key
#   text_type    = "transcript" | "soap" | "evidence_chunk"
#   text_snippet = first 500 chars (for debugging)
#   vector       = float[1536]   (Ada-002)
#   created_at   = ISO-8601
# TTL: 365 days (embeddings are expensive to regenerate)
#
# Note: IVF/vector index requires Cosmos DB for NoSQL with vector search
# feature enabled. The vectorEmbeddingPolicy and indexing policy below
# follow the GA API (azurerm 4.x uses the azapi_resource workaround until
# the provider exposes the vector_embedding_policy block natively).

resource "azurerm_cosmosdb_sql_container" "embeddings" {
  name                = "embeddings"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/encounter_id"]

  default_ttl = 365 * 24 * 60 * 60

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/vector/*" # Exclude raw vector from standard index
    }
  }
}

# ── Container: traces ─────────────────────────────────────────────────────
# OpenTelemetry-style traces emitted by each agent step.
# Used by the Phase 5 eval runner to measure latency per agent.
#
# Schema:
#   id           = trace_id (UUID)
#   encounter_id = partition key
#   span_name    = agent step name
#   parent_span  = null | trace_id
#   start_time   = ISO-8601
#   end_time     = ISO-8601
#   attributes   = {}  (key-value bag)
#   status       = "OK" | "ERROR"
# TTL: 30 days (high volume; shorter retention than agent_runs)

resource "azurerm_cosmosdb_sql_container" "traces" {
  name                = "traces"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/encounter_id"]

  default_ttl = 30 * 24 * 60 * 60

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/attributes/_payload" # Large free-form payload
    }
  }
}

# ── Diagnostic Settings ────────────────────────────────────────────────────
# Forward Cosmos request/throttle metrics to Log Analytics.
# Skipped when log_analytics_workspace_id is empty (lab sub).

resource "azurerm_monitor_diagnostic_setting" "cosmos" {
  count = var.log_analytics_workspace_id != "" ? 1 : 0

  name                       = "${var.name_prefix}-cosmos-diag"
  target_resource_id         = azurerm_cosmosdb_account.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  metric {
    category = "Requests"
  }

  enabled_log {
    category = "DataPlaneRequests"
  }

  enabled_log {
    category = "QueryRuntimeStatistics"
  }
}
