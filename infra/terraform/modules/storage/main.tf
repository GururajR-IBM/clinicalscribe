# Storage account name must be 3-24 chars, lowercase alphanumeric only, globally unique.
# We strip hyphens from name_prefix and truncate to fit.
locals {
  sa_name = substr(replace("${var.name_prefix}media", "-", ""), 0, 24)
}

resource "azurerm_storage_account" "media" {
  name                     = local.sa_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  # Security hardening
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  https_traffic_only_enabled      = true
  shared_access_key_enabled       = true # needed until workload identity wired in Phase 1.9

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  tags = var.tags
}

resource "azurerm_storage_container" "encounter_media" {
  name                  = "encounter-media"
  storage_account_id    = azurerm_storage_account.media.id
  container_access_type = "private"
}

resource "azurerm_storage_management_policy" "media_lifecycle" {
  storage_account_id = azurerm_storage_account.media.id

  rule {
    name    = "delete-old-media"
    enabled = true
    filters {
      prefix_match = ["encounter-media/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = var.media_retention_days
      }
    }
  }
}

resource "azurerm_monitor_diagnostic_setting" "storage" {
  count = var.log_analytics_workspace_id != "" ? 1 : 0

  name                       = "${var.name_prefix}-storage-diag"
  target_resource_id         = "${azurerm_storage_account.media.id}/blobServices/default"
  log_analytics_workspace_id = var.log_analytics_workspace_id

  metric {
    category = "Transaction"
  }
}
