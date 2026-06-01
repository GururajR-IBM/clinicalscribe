output "log_analytics_workspace_id" {
  description = "Log Analytics workspace resource ID."
  value       = azurerm_log_analytics_workspace.main.id
}

output "log_analytics_workspace_name" {
  description = "Log Analytics workspace name."
  value       = azurerm_log_analytics_workspace.main.name
}

output "application_insights_id" {
  description = "Application Insights resource ID."
  value       = azurerm_application_insights.main.id
}

output "application_insights_connection_string" {
  description = "App Insights connection string (write to Key Vault, do not log)."
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

output "application_insights_instrumentation_key" {
  description = "App Insights instrumentation key (legacy; prefer connection_string)."
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}
