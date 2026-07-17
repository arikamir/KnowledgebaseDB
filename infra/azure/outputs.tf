output "resource_group_name" { value = azurerm_resource_group.app.name }
output "aks_cluster_name" { value = azurerm_kubernetes_cluster.app.name }
output "acr_login_server" { value = azurerm_container_registry.app.login_server }
output "acr_id" { value = azurerm_container_registry.app.id }
output "aks_oidc_issuer_url" { value = azurerm_kubernetes_cluster.app.oidc_issuer_url }
output "kubelet_identity_object_id" { value = azurerm_kubernetes_cluster.app.kubelet_identity[0].object_id }
output "key_vault_id" { value = azurerm_key_vault.app.id }
output "managed_redis_id" { value = azurerm_managed_redis.bff.id }
output "postgresql_id" { value = azurerm_postgresql_flexible_server.core.id }
output "evidence_hold_authorization" {
  description = "Non-secret hold-manager/reconciler assignment and denial contract."
  value = {
    contract                        = local.evidence_hold_authorization_contract
    manager_inventory_assignment    = azurerm_role_assignment.evidence_hold_manager_inventory.id
    manager_audit_assignment        = azurerm_role_assignment.evidence_hold_manager_audit.id
    reconciler_inventory_assignment = azurerm_role_assignment.evidence_hold_reconciler_inventory.id
    reconciler_version_assignment   = azurerm_role_assignment.evidence_hold_reconciler_versions.id
  }
}
output "gateway_certificate_dns_bootstrap" {
  description = "Non-secret certificate-version, trust, DNS, and least-privilege rotation metadata."
  value = {
    browser_url                  = "https://${local.public_gateway_hostname}/"
    browser_dns_record_id        = azurerm_dns_cname_record.browser.id
    browser_validation_record_id = azurerm_dns_txt_record.browser_certificate_validation.id
    private_core_url             = "https://${local.private_core_hostname}/"
    private_core_dns_record_id   = azurerm_private_dns_a_record.core.id
    certificate_versions         = local.gateway_certificate_versions
    rotation_identity_id         = azurerm_user_assigned_identity.workload["gateway-certificate-dns"].id
    certificate_assignment_ids   = { for name, assignment in azurerm_role_assignment.gateway_certificate_versions : name => assignment.id }
    dns_assignment_ids           = { for name, assignment in azurerm_role_assignment.gateway_named_dns_records : name => assignment.id }
    private_key_exportable       = false
  }
}
output "application_url_lookup_command" {
  description = "Run after the Kubernetes deployment to print the browser URL."
  value       = "bash .agents/skills/provision-azure-app-resources/scripts/get-application-url.sh"
}
