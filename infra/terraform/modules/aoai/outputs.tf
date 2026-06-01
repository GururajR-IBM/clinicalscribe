output "aoai_id" {
  description = "Azure OpenAI resource ID."
  value       = azurerm_cognitive_account.aoai.id
}

output "aoai_endpoint" {
  description = "Azure OpenAI endpoint URL."
  value       = azurerm_cognitive_account.aoai.endpoint
}

output "aoai_name" {
  description = "Azure OpenAI account name."
  value       = azurerm_cognitive_account.aoai.name
}

output "aoai_primary_key" {
  description = "Primary access key — store in Key Vault; never log."
  value       = azurerm_cognitive_account.aoai.primary_access_key
  sensitive   = true
}
