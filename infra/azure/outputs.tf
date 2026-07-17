output "resource_group_name" { value = azurerm_resource_group.app.name }
output "aks_cluster_name" { value = azurerm_kubernetes_cluster.app.name }
output "acr_login_server" { value = azurerm_container_registry.app.login_server }
output "acr_id" { value = azurerm_container_registry.app.id }
output "aks_oidc_issuer_url" { value = azurerm_kubernetes_cluster.app.oidc_issuer_url }
output "kubelet_identity_object_id" { value = azurerm_kubernetes_cluster.app.kubelet_identity[0].object_id }
output "key_vault_id" { value = azurerm_key_vault.app.id }
output "managed_redis_id" { value = azurerm_managed_redis.bff.id }
output "postgresql_id" { value = azurerm_postgresql_flexible_server.core.id }
output "application_url_lookup_command" {
  description = "Run after the Kubernetes deployment to print the browser URL."
  value       = "bash .agents/skills/provision-azure-app-resources/scripts/get-application-url.sh"
}
