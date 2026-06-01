# -----------------------------------------------------------------------------
# Container Apps module
# -----------------------------------------------------------------------------
# Hosts all ClinicalScribe runtime services (gateway, orchestrator, ingestion-
# worker, eval-runner, 4 MCP servers, Next.js web) on Azure Container Apps.
#
# Cost model:
#   - Consumption workload profile, scale-to-zero (min_replicas = 0)
#   - ACR Basic SKU (~$5/mo flat) for image storage
#   - LAW retention controlled by observability module (30 days default)
#   - Idle cost when nothing is invoked: ~$5 (just the ACR)
#
# Identity model:
#   - One user-assigned managed identity shared by every app
#   - Granted AcrPull on the ACR + Key Vault Secrets User on the KV
#   - Apps reference KV secrets via secret_env (resolved at container start)
# -----------------------------------------------------------------------------

resource "azurerm_user_assigned_identity" "apps" {
  name                = "${var.name_prefix}-aca-id"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_container_registry" "main" {
  name                = replace("${var.name_prefix}acr", "-", "")
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.acr_sku
  admin_enabled       = false
  tags                = var.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.apps.principal_id
}

resource "azurerm_role_assignment" "kv_secrets" {
  count                = var.key_vault_id != "" ? 1 : 0
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.apps.principal_id
}

resource "azurerm_container_app_environment" "main" {
  name                       = "${var.name_prefix}-aca-env"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = var.log_analytics_workspace_id
  tags                       = var.tags
}

# -----------------------------------------------------------------------------
# One azurerm_container_app per entry in var.services (for_each).
# -----------------------------------------------------------------------------
resource "azurerm_container_app" "svc" {
  for_each = var.services

  name                         = "${var.name_prefix}-${each.key}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  tags                         = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.apps.id
  }

  dynamic "secret" {
    for_each = each.value.secret_env
    content {
      name                = lower(replace(secret.key, "_", "-"))
      identity            = azurerm_user_assigned_identity.apps.id
      key_vault_secret_id = "${var.key_vault_id}/secrets/${secret.value}"
    }
  }

  template {
    min_replicas = each.value.min_replicas
    max_replicas = each.value.max_replicas

    container {
      name   = each.key
      image  = "${azurerm_container_registry.main.login_server}/${each.value.image_repo}:${var.image_tag}"
      cpu    = each.value.cpu
      memory = each.value.memory

      dynamic "env" {
        for_each = each.value.env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = each.value.secret_env
        content {
          name        = env.key
          secret_name = lower(replace(env.key, "_", "-"))
        }
      }
    }
  }

  dynamic "ingress" {
    for_each = each.value.port == null ? [] : [1]
    content {
      external_enabled = each.value.external
      target_port      = each.value.port
      transport        = "auto"
      traffic_weight {
        latest_revision = true
        percentage      = 100
      }
    }
  }

  depends_on = [azurerm_role_assignment.acr_pull]
}
