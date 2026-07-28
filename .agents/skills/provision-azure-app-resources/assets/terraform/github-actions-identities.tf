locals {
  workload_identity_subjects = {
    bff                      = "system:serviceaccount:career-agent:bff", core = "system:serviceaccount:career-agent:core"
    lifecycle                = "system:serviceaccount:career-agent:lifecycle", retention = "system:serviceaccount:career-agent:retention"
    lab-revalidation         = "system:serviceaccount:career-agent:lab-revalidation", migration = "system:serviceaccount:career-migrations:core-migrator"
    evidence-hold-reconciler = "system:serviceaccount:career-agent:evidence-hold-reconciler"
    alb-controller           = "system:serviceaccount:azure-alb-system:alb-controller-sa"
    gateway-certificate-dns  = "system:serviceaccount:career-agent:gateway-certificate-rotation"
  }
  workload_identity_contract = {
    bff                      = { allowed = ["redis-session", "core-delegated-token", "named-key-vault-certificate"], denied = ["postgresql", "acr", "aks", "evidence", "other-key-vault-secret"] }
    core                     = { allowed = ["postgresql-application-dml", "named-signing-key-metadata"], denied = ["redis", "graph", "acr", "aks", "evidence", "terraform-state"] }
    lifecycle                = { allowed = ["graph-known-user-read", "bff-session-revoke", "lifecycle-outbox"], denied = ["learning-row-write", "retention-procedure", "acr", "aks"] }
    retention                = { allowed = ["audited-retention-claim-process-procedures"], denied = ["direct-queue-read", "direct-learning-read", "eligibility-tamper", "acr", "aks"] }
    lab-revalidation         = { allowed = ["lab-destination-status-counter"], denied = ["employee-learning-data", "content-publish", "acr", "aks"] }
    migration                = { allowed = ["postgresql-ddl-backfill-via-migrator-pod"], denied = ["aks-api", "secrets", "application-dml", "other-database"] }
    evidence-hold-reconciler = { allowed = ["hold-inventory-read", "exact-version-legal-hold-set-clear"], denied = ["blob-content-read-list-delete", "evidence-create", "fixed-policy-mutation"] }
    alb-controller           = { allowed = ["exact-agc-resource-group-configuration", "exact-subnet-join"], denied = ["aks-admin", "dns", "key-vault", "data-services", "unrelated-network"] }
    gateway-certificate-dns  = { allowed = ["named-certificate-version-read", "named-dns-record-write"], denied = ["private-key-export", "unrelated-certificate", "zone-destroy", "agc", "aks", "identity-admin", "data-services"] }
  }
  delivery_identity_contract = {
    ui        = { identity = "none", allowed = [], denied = ["azure-token", "workload-identity", "acr", "aks", "evidence"] }
    validator = { identity = "none", allowed = [], denied = ["azure-token", "acr-push", "aks-mutate", "evidence-write", "terraform"] }
    publisher = { identity = "user-assigned", allowed = ["exact-acr-push", "environment-prefix-evidence-create-and-exact-verify"], denied = ["aks", "target-rg-reader", "terraform-state", "key-vault-secret", "redis-data", "postgresql-data", "evidence-list-delete-overwrite"] }
    kubelet   = { identity = "aks-kubelet-non-federatable", allowed = ["exact-acr-pull"], denied = ["acr-push-delete-import-admin", "role-assignment", "federation", "application-pod-assumption"] }
  }
}
resource "azurerm_user_assigned_identity" "workload" {
  for_each            = local.workload_identity_subjects
  name                = "id-${local.stem}-${each.key}"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  tags                = local.tags
}
resource "azurerm_federated_identity_credential" "workload" {
  for_each  = local.workload_identity_subjects
  name      = "fic-${each.key}"
  parent_id = azurerm_user_assigned_identity.workload[each.key].id
  issuer    = azurerm_kubernetes_cluster.app.oidc_issuer_url
  audience  = ["api://AzureADTokenExchange"]
  subject   = each.value
}
resource "azurerm_user_assigned_identity" "github_actions_publisher" {
  name                = "id-${local.stem}-github-actions-publisher"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  tags                = local.tags
}
resource "azurerm_role_assignment" "publisher_exact_acr_push" {
  scope                = azurerm_container_registry.app.id
  role_definition_name = "AcrPush"
  principal_id         = azurerm_user_assigned_identity.github_actions_publisher.principal_id
}
resource "azurerm_federated_identity_credential" "github_actions_publisher" {
  name                = "github-actions-publisher-${var.environment}"
  resource_group_name = azurerm_resource_group.app.name
  parent_id           = azurerm_user_assigned_identity.github_actions_publisher.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:${split("/", var.github_repository)[0]}@${var.github_repository_owner_id}/${split("/", var.github_repository)[1]}@${var.github_repository_id}:environment:${var.github_actions_environment}-publisher"
}
output "workload_identity_manifest" { value = { for name, identity in azurerm_user_assigned_identity.workload : name => { resource_id = identity.id, client_id = identity.client_id, principal_id = identity.principal_id, subject = local.workload_identity_subjects[name], contract = local.workload_identity_contract[name] } } }
output "github_actions_delivery_identity_manifest" { value = { publisher = { resource_id = azurerm_user_assigned_identity.github_actions_publisher.id, client_id = azurerm_user_assigned_identity.github_actions_publisher.client_id, subject = azurerm_federated_identity_credential.github_actions_publisher.subject }, issuer = "https://token.actions.githubusercontent.com", audience = "api://AzureADTokenExchange", validator = null, ui = null, contract = local.delivery_identity_contract } }
