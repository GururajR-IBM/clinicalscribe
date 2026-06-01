output "apim_name" {
  value = azurerm_api_management.main.name
}

output "gateway_url" {
  value = azurerm_api_management.main.gateway_url
}

output "management_api_url" {
  value = azurerm_api_management.main.management_api_url
}
