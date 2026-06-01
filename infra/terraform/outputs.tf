output "resource_group_name" {
  description = "Name of the primary resource group."
  value       = azurerm_resource_group.main.name
}

output "location" {
  description = "Primary region."
  value       = azurerm_resource_group.main.location
}
