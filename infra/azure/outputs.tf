output "resource_group_name" { value = azurerm_resource_group.app.name }
output "aks_cluster_name" { value = azurerm_kubernetes_cluster.app.name }
output "acr_login_server" { value = azurerm_container_registry.app.login_server }
output "acr_id" { value = azurerm_container_registry.app.id }
output "application_url_lookup_command" {
  description = "Run after the Kubernetes deployment to print the browser URL."
  value       = "bash .agents/skills/provision-azure-app-resources/scripts/get-application-url.sh"
}
