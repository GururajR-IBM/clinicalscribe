output "account_endpoint" {
  description = "Cosmos DB NoSQL account endpoint."
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "account_name" {
  value = azurerm_cosmosdb_account.main.name
}

output "database_name" {
  value = azurerm_cosmosdb_sql_database.main.name
}

output "primary_key" {
  description = "Primary master key — store in Key Vault, never in source."
  value       = azurerm_cosmosdb_account.main.primary_key
  sensitive   = true
}

output "connection_string" {
  value     = "AccountEndpoint=${azurerm_cosmosdb_account.main.endpoint};AccountKey=${azurerm_cosmosdb_account.main.primary_key};"
  sensitive = true
}
