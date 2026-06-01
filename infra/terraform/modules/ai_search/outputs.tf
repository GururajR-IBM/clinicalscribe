output "service_name" {
  value = azurerm_search_service.main.name
}

output "endpoint" {
  value = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "primary_key" {
  value     = azurerm_search_service.main.primary_key
  sensitive = true
}

output "index_name" {
  description = "The clinical knowledge base index name."
  value       = "clinical-kb"
}
