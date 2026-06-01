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

# -- Container Apps (compute plane: ACR + ACA env + 9 apps, scale-to-zero) ---
# All 9 services run here. Internal DNS = <app>.internal.<env-domain>; only
# gateway + web are external. AOAI is BYO via env vars on each app.
# module "container_apps" {
#   source                     = "./modules/container_apps"
#   name_prefix                = local.name_prefix
#   location                   = azurerm_resource_group.main.location
#   resource_group_name        = azurerm_resource_group.main.name
#   tags                       = local.tags
#   log_analytics_workspace_id = module.observability.log_analytics_workspace_id
#   key_vault_id               = module.keyvault.id
#   image_tag                  = var.image_tag
#
#   services = {
#     gateway = {
#       image_repo = "gateway"
#       port       = 8000
#       external   = true
#       env = {
#         ORCHESTRATOR_URL = "https://${local.name_prefix}-orchestrator.internal.${module.container_apps.environment_id}"
#         CLERK_JWKS_URL   = var.clerk_jwks_uri
#       }
#     }
#     orchestrator = {
#       image_repo   = "orchestrator"
#       port         = 8001
#       external     = false
#       cpu          = 0.5
#       memory       = "1Gi"
#       max_replicas = 5
#       env = {
#         AOAI_ENDPOINT        = var.aoai_endpoint
#         AOAI_DRAFT_MODEL     = "gpt-4o-mini"
#         AOAI_REVIEW_MODEL    = "gpt-4o-mini"
#         AOAI_EMBEDDING_MODEL = "text-embedding-3-small"
#         COSMOS_ENDPOINT      = module.cosmos.endpoint
#         MCP_MEDICAL_KB_URL   = "http://${local.name_prefix}-mcp-medical-kb"
#         MCP_CODING_URL       = "http://${local.name_prefix}-mcp-coding"
#         MCP_EHR_URL          = "http://${local.name_prefix}-mcp-ehr"
#         MCP_DRUG_URL         = "http://${local.name_prefix}-mcp-drug"
#       }
#       secret_env = { AOAI_KEY = "aoai-key", COSMOS_KEY = "cosmos-key" }
#     }
#     "ingestion-worker" = {
#       image_repo = "ingestion-worker"
#       env = {
#         AOAI_ENDPOINT             = var.aoai_endpoint
#         AOAI_WHISPER_DEPLOYMENT   = "whisper"
#         ORCHESTRATOR_BASE_URL     = "http://${local.name_prefix}-orchestrator"
#       }
#       secret_env = {
#         AOAI_KEY                          = "aoai-key"
#         DATABASE_URL                      = "postgres-url"
#         AZURE_STORAGE_CONNECTION_STRING   = "storage-conn"
#       }
#     }
#     "mcp-medical-kb"   = { image_repo = "mcp-medical-kb",   port = 8010, external = false }
#     "mcp-coding"       = { image_repo = "mcp-coding",       port = 8011, external = false }
#     "mcp-ehr"          = { image_repo = "mcp-ehr",          port = 8012, external = false }
#     "mcp-drug"         = { image_repo = "mcp-drug",         port = 8013, external = false }
#     web = {
#       image_repo = "web"
#       port       = 3000
#       external   = true
#       env = {
#         NEXT_PUBLIC_GATEWAY_URL = "https://${module.container_apps.app_fqdns["gateway"]}"
#       }
#     }
#   }
# }
