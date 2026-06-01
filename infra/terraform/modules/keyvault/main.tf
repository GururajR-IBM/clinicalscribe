data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                = "${var.name_prefix}-kv"
  location            = var.location
  resource_group_name = var.resource_group_name
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  # RBAC model — no legacy access policies
  rbac_authorization_enabled = true

  # Soft-delete (mandatory since 2020, 90 days)
  soft_delete_retention_days = 90
  purge_protection_enabled   = false # keep false for lab; set true for prod

  network_acls {
    default_action = "Allow" # tighten to "Deny" + VNet rules in prod
    bypass         = "AzureServices"
  }

  tags = var.tags
}

# Grant Key Vault Administrator to each admin object ID
resource "azurerm_role_assignment" "kv_admin" {
  for_each = toset(var.admin_object_ids)

  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = each.value
}

resource "azurerm_monitor_diagnostic_setting" "keyvault" {
  name                       = "${var.name_prefix}-kv-diag"
  target_resource_id         = azurerm_key_vault.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "AuditEvent"
  }

  metric {
    category = "AllMetrics"
  }
}
