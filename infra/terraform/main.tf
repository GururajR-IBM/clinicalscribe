locals {
  default_tags = {
    project     = var.project
    environment = var.environment
    owner       = var.owner
    managed_by  = "terraform"
    repo        = "github.com/GururajR-IBM/clinicalscribe"
  }
  tags = merge(local.default_tags, var.tags)

  # Resource naming: <project>-<env>-<resource>
  name_prefix = "${var.project}-${var.environment}"
}

# ── Pending modules (added per phase) ──────────────────────────────────────
# ── Pending modules (added per phase) ──────────────────────────────────────
# Phase 1 remaining:
#   - module "network"      (VNet + subnets + NSG)           task 1.1 pre-req
#   - module "aks"          (cluster, workload identity)      task 1.1
#   - module "aoai"         (Azure OpenAI + deployments)      task 1.2
#   - module "postgres"     (Postgres Flexible Server)        task 1.3
#   - module "speech"       (Azure AI Speech)                 task 1.8
# Phase 6:
#   - module "apim"         (APIM Consumption)

# ── Resource Group ──────────────────────────────────────────────────────────
resource "azurerm_resource_group" "main" {
  name     = "${local.name_prefix}-rg"
  location = var.location
  tags     = local.tags
}

# ── Phase 1.7 — Observability (Log Analytics + App Insights) ───────────────
# BLOCKED on lab sub by policy AI-3016:Lab04. Enable when on PAYG.
# module "observability" {
#   source = "./modules/observability"
#   name_prefix         = local.name_prefix
#   location            = azurerm_resource_group.main.location
#   resource_group_name = azurerm_resource_group.main.name
#   tags                = local.tags
# }

# ── Phase 1.5 — Blob Storage (encounter-media) ─────────────────────────────
# BLOCKED on lab sub by policy AI-3016:Lab04. Enable when on PAYG.
# module "storage" {
#   source = "./modules/storage"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }

# ── Phase 1.6 — Key Vault ──────────────────────────────────────────────────
# BLOCKED on lab sub by policy AI-3016:Lab04. Enable when on PAYG.
# module "keyvault" {
#   source = "./modules/keyvault"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   tenant_id                  = var.tenant_id
#   admin_object_ids           = var.kv_admin_object_ids
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }

# ── Phase 1.2 — Azure OpenAI ───────────────────────────────────────────────
# BLOCKED on lab sub by policy AI-3016:Lab04. Enable when on PAYG.
# module "aoai" {
#   source = "./modules/aoai"
#   name_prefix         = local.name_prefix
#   location            = azurerm_resource_group.main.location
#   resource_group_name = azurerm_resource_group.main.name
#   tags                = local.tags
# }

# ── Phase 3.1–3.3 — Cosmos DB NoSQL ───────────────────────────────────────
# Containers: agent_runs, evidence, embeddings, traces
# BLOCKED on lab sub by policy AI-3016:Lab04. Enable when on PAYG.
# module "cosmos" {
#   source = "./modules/cosmos"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }

# ── Phase 3.5 — AI Search (hybrid BM25 + Ada-002 vector + semantic reranker)
# Index: clinical-kb  (index JSON: scripts/search/create_index.json)
# BLOCKED on lab sub by policy AI-3016:Lab04. Enable when on PAYG.
# module "ai_search" {
#   source = "./modules/ai_search"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   sku                        = var.environment == "prod" ? "standard" : "basic"
#   replica_count              = var.environment == "prod" ? 2 : 1
#   aoai_endpoint              = module.aoai.endpoint
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }

# ── Phase 4 — Postgres Flexible Server ────────────────────────────────────
# Schema: users, encounters, notes, codes, approvals, audit_log, drug_interaction_warnings
# Migrations: db/alembic/ (alembic upgrade head)
# BLOCKED on lab sub by policy AI-3016:Lab04. Enable when on PAYG.
# module "postgres" {
#   source = "./modules/postgres"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   sku_name                   = var.environment == "prod" ? "GP_Standard_D2s_v3" : "B_Standard_B1ms"
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }

# -- Phase 6 -- VNet + subnets + NSGs + private DNS + private endpoints --
# BLOCKED on lab sub by policy AI-3016:Lab04. Enable when on PAYG.
# module "network" {
#   source = "./modules/network"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }

# -- Phase 6 -- APIM Consumption gateway (Clerk JWT + rate limit) --
# BLOCKED on lab sub by policy AI-3016:Lab04. Enable when on PAYG.
# module "apim" {
#   source                     = "./modules/apim"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   sku_name                   = var.environment == "prod" ? "Developer_1" : "Consumption_0"
#   clerk_jwks_uri             = var.clerk_jwks_uri
#   gateway_backend_url        = var.gateway_backend_url
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }