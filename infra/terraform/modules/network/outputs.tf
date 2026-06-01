output "vnet_id" {
  value = azurerm_virtual_network.main.id
}

output "vnet_name" {
  value = azurerm_virtual_network.main.name
}

output "subnet_aks_id" {
  value = azurerm_subnet.aks.id
}

output "subnet_postgres_id" {
  value = azurerm_subnet.postgres.id
}

output "subnet_private_endpoints_id" {
  value = azurerm_subnet.private_endpoints.id
}

output "postgres_private_dns_zone_id" {
  value = azurerm_private_dns_zone.postgres.id
}
