# ── Azure AI Search Service ────────────────────────────────────────────────
#
# Hosts the "clinical-kb" index used by the Retrieval Agent (Agent 3).
# Index schema:
#   - id          (string, key)
#   - title       (string, searchable, retrievable)
#   - content     (string, searchable, retrievable)
#   - icd10       (string, filterable, retrievable)
#   - source      (string, filterable, retrievable)
#   - document_type (string, filterable) — "guideline" | "drug_label" | "kb_entry"
#   - content_vector (Collection(Edm.Single), 1536 dims — Ada-002)
#
# Search mode: hybrid — BM25 keyword + Ada-002 vector + semantic reranker.
# Semantic configuration: "clinical-semantic-config" (title/content fields).
#
# Note: Semantic ranker is only available on standard SKU and above.
# For basic SKU (lab), vector + BM25 runs without semantic reranking.
#
# Index creation: the azurerm provider does not manage search indexes.
# The index JSON is defined in scripts/search/create_index.json and applied
# by scripts/search/deploy_index.sh (called from CI on PAYG environments).

resource "azurerm_search_service" "main" {
  name                = "${var.name_prefix}-search"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
  replica_count       = var.replica_count
  partition_count     = var.partition_count
  tags                = var.tags

  # Semantic ranking (requires standard+)
  semantic_search_sku = var.sku == "basic" || var.sku == "free" ? null : "free"

  # RBAC — disable API-key auth once Workload Identity is configured (Phase 6)
  local_authentication_enabled = true
  public_network_access_enabled = true   # Set false + private endpoint in Phase 6
}

# ── Diagnostic settings ────────────────────────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "search" {
  count = var.log_analytics_workspace_id != "" ? 1 : 0

  name                       = "${var.name_prefix}-search-diag"
  target_resource_id         = azurerm_search_service.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  metric {
    category = "AllMetrics"
  }

  enabled_log {
    category = "OperationLogs"
  }
}
