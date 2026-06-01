output "acr_login_server" {
  description = "ACR login server (push images here: docker push <server>/<repo>:<tag>)."
  value       = azurerm_container_registry.main.login_server
}

output "acr_name" {
  description = "ACR resource name."
  value       = azurerm_container_registry.main.name
}

output "environment_id" {
  description = "Container Apps environment ID."
  value       = azurerm_container_app_environment.main.id
}

output "identity_principal_id" {
  description = "Principal ID of the shared user-assigned identity (AcrPull + KV Secrets User)."
  value       = azurerm_user_assigned_identity.apps.principal_id
}

output "app_fqdns" {
  description = "Map of app name -> FQDN for apps with ingress enabled."
  value = {
    for k, app in azurerm_container_app.svc :
    k => try(app.ingress[0].fqdn, null)
  }
}
