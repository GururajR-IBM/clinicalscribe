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

# -----------------------------------------------------------------------------
# All module blocks below are commented out so `terraform apply` is a no-op
# until the operator opts in. Uncomment the blocks you need. Cost-optimized
# defaults (Cosmos serverless, Postgres B1ms, AI Search basic, APIM Consumption,
# LAW 30-day retention) keep an idle deployment well under $50/month.
#
# Bring-your-own LLM: Azure OpenAI is NOT provisioned by this stack. The
# orchestrator + eval-runner read AOAI_ENDPOINT + AOAI_KEY from env vars and
# can target any AOAI account (e.g. one owned by a different subscription).
# -----------------------------------------------------------------------------

resource "azurerm_resource_group" "main" {
  name     = "${local.name_prefix}-rg"
  location = var.location
  tags     = local.tags
}

# -- Observability: Log Analytics + App Insights ------------------------------
# module "observability" {
#   source              = "./modules/observability"
#   name_prefix         = local.name_prefix
#   location            = azurerm_resource_group.main.location
#   resource_group_name = azurerm_resource_group.main.name
#   tags                = local.tags
#   log_retention_days  = 30
# }

# -- Blob Storage (encounter-media) -------------------------------------------
# module "storage" {
#   source                     = "./modules/storage"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }

# -- Key Vault ----------------------------------------------------------------
# module "keyvault" {
#   source                     = "./modules/keyvault"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   tenant_id                  = var.tenant_id
#   admin_object_ids           = var.kv_admin_object_ids
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }

# -- Cosmos DB NoSQL (serverless: pay-per-request) ----------------------------
# Containers: agent_runs, evidence, embeddings, traces
# module "cosmos" {
#   source                     = "./modules/cosmos"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }

# -- AI Search (hybrid: BM25 + vector + semantic reranker on standard SKU) ---
# Index: clinical-kb (scripts/search/create_index.json)
# module "ai_search" {
#   source                     = "./modules/ai_search"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   sku                        = var.environment == "prod" ? "standard" : "basic"
#   replica_count              = 1
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }

# -- Postgres Flexible Server -------------------------------------------------
# Migrations: db/alembic/ (alembic upgrade head)
# module "postgres" {
#   source                     = "./modules/postgres"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   sku_name                   = var.environment == "prod" ? "GP_Standard_D2s_v3" : "B_Standard_B1ms"
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }

# -- VNet + subnets + NSGs + private DNS + private endpoints (PAYG only) -----
# module "network" {
#   source                     = "./modules/network"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
# }

# -- APIM (Consumption tier — Clerk JWT + rate limit) ------------------------
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
