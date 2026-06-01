# ── Postgres Flexible Server ───────────────────────────────────────────────
#
# Hosts the relational schema (users, encounters, notes, codes, approvals, audit_log).
# Migrations managed by Alembic (db/alembic/).
#
# Access modes:
#   lab/dev  — public access (authentication_only; firewall allows Azure services)
#   prod     — private access via delegated subnet + private DNS zone

resource "random_password" "postgres" {
  length           = 32
  special          = true
  override_special = "!#$%^&*()-_=+[]{}|;:,.<>?"
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${var.name_prefix}-pgflex"
  resource_group_name    = var.resource_group_name
  location               = var.location
  version                = var.postgres_version
  administrator_login    = var.admin_username
  administrator_password = random_password.postgres.result
  sku_name               = var.sku_name
  storage_mb             = var.storage_mb
  tags                   = var.tags

  # Private access when subnet is provided; otherwise public
  delegated_subnet_id = var.delegated_subnet_id != "" ? var.delegated_subnet_id : null
  private_dns_zone_id = var.private_dns_zone_id != "" ? var.private_dns_zone_id : null

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false # enable in prod Phase 6

  high_availability {
    mode = "Disabled" # enable SameZone or ZoneRedundant in prod Phase 6
  }

  maintenance_window {
    day_of_week  = 0 # Sunday
    start_hour   = 2
    start_minute = 0
  }
}

# ── Database ───────────────────────────────────────────────────────────────

resource "azurerm_postgresql_flexible_server_database" "clinicalscribe" {
  name      = "clinicalscribe"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# ── Firewall rules ─────────────────────────────────────────────────────────
# Allow Azure services (GitHub Actions runner, AKS egress) to reach the server.
# In prod, replace with private endpoint and remove firewall rules.

resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  count            = var.delegated_subnet_id == "" ? 1 : 0
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ── Server configuration ───────────────────────────────────────────────────

resource "azurerm_postgresql_flexible_server_configuration" "log_statement" {
  name      = "log_statement"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "ddl" # Log DDL statements for audit
}

resource "azurerm_postgresql_flexible_server_configuration" "log_min_duration" {
  name      = "log_min_duration_statement"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "1000" # Log queries slower than 1 s
}

# ── Diagnostic settings ────────────────────────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "postgres" {
  count = var.log_analytics_workspace_id != "" ? 1 : 0

  name                       = "${var.name_prefix}-postgres-diag"
  target_resource_id         = azurerm_postgresql_flexible_server.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  metric {
    category = "AllMetrics"
  }

  enabled_log {
    category = "PostgreSQLLogs"
  }
}
