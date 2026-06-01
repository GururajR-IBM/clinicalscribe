locals {
  default_tags = {
    project     = var.project
    environment = var.environment
    owner       = var.owner
    managed_by  = "terraform"
    repo        = "github.com/GururajR-IBM/clinicalscribe"
  }
  tags = merge(local.default_tags, var.tags)

  # Resource naming: <project>-<env>-<resource>-<region-short>
  name_prefix = "${var.project}-${var.environment}"
}

# Phase 0: this file is intentionally minimal. Phase 1 wires in:
#   - module "network"  (VNet + subnets + NSG)
#   - module "aks"      (cluster, workload identity, OIDC issuer)
#   - module "data"     (Cosmos NoSQL, Postgres Flex, Blob)
#   - module "ai"       (Azure OpenAI, Speech, Doc Intel, Content Safety)
#   - module "search"   (AI Search)
#   - module "messaging"(Service Bus)
#   - module "observability" (Log Analytics, App Insights)
# Phase 6 adds:
#   - module "apim"     (APIM Consumption)

resource "azurerm_resource_group" "main" {
  name     = "${local.name_prefix}-rg"
  location = var.location
  tags     = local.tags
}
