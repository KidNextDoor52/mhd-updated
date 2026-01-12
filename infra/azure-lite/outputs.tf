output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "container_app_name" {
  value = azurerm_container_app.api.name
}

output "container_app_fqdn" {
  value = azurerm_container_app.api.ingress[0].fqdn
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "acr_name" {
  value = azurerm_container_registry.acr.name
}

output "storage_account_name" {
  value = azurerm_storage_account.sa.name
}
