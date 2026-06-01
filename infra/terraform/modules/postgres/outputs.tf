output "fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "server_name" {
  value = azurerm_postgresql_flexible_server.main.name
}

output "admin_username" {
  value = var.admin_username
}

output "admin_password" {
  value     = random_password.postgres.result
  sensitive = true
}

output "database_url" {
  description = "asyncpg-style connection string for runtime services."
  value       = "postgresql+asyncpg://${var.admin_username}:${random_password.postgres.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/clinicalscribe"
  sensitive   = true
}

output "alembic_database_url" {
  description = "psycopg2-style connection string for Alembic migrations."
  value       = "postgresql://${var.admin_username}:${random_password.postgres.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/clinicalscribe"
  sensitive   = true
}
