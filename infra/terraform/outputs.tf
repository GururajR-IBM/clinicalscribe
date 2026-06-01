output "resource_group_name" {
  description = "Name of the primary resource group."
  value       = azurerm_resource_group.main.name
}

output "location" {
  description = "Primary region."
  value       = azurerm_resource_group.main.location
}

# ── Observability — BLOCKED on lab (enable on PAYG) ───────────────────────
# output "log_analytics_workspace_id" { ... }
# output "log_analytics_workspace_name" { ... }
# output "application_insights_id" { ... }
# output "application_insights_connection_string" { ... }

# ── Storage — BLOCKED on lab (enable on PAYG) ─────────────────────────────
# output "storage_account_name" { ... }
# output "encounter_media_container_name" { ... }

# ── Key Vault — BLOCKED on lab (enable on PAYG) ───────────────────────────
# output "key_vault_name" { ... }
# output "key_vault_uri" { ... }

# ── Azure OpenAI ──────────────────────────────────────────────────────────
# Not provisioned by this stack — bring-your-own AOAI account via env vars
# (AOAI_ENDPOINT, AOAI_KEY). See README.md.
