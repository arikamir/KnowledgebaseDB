locals {
  # This contract is emitted into the reviewed bootstrap manifest. Positive
  # grants are exact; everything listed under denied remains a validation case.
  delivery_identity_contract = {
    ui        = { identity = "none", allowed = [], denied = ["azure-token", "workload-identity", "acr", "aks", "evidence"] }
    validator = { identity = "none", allowed = [], denied = ["azure-token", "acr-push", "aks-mutate", "evidence-write", "terraform"] }
    publisher = {
      identity = "user-assigned"
      allowed  = ["exact-acr-push", "environment-prefix-evidence-create-and-exact-verify"]
      denied   = ["aks", "target-rg-reader", "terraform-state", "key-vault-secret", "redis-data", "postgresql-data", "evidence-list-delete-overwrite"]
    }
    deployer = {
      identity = "user-assigned"
      allowed  = ["exact-aks-deploy", "target-rg-reader", "environment-prefix-evidence-create-and-exact-verify"]
      denied   = ["acr-push-delete-import-admin", "terraform-state", "key-vault-secret", "redis-data", "postgresql-data", "evidence-list-delete-overwrite"]
    }
    kubelet = {
      identity = "aks-kubelet-non-federatable"
      allowed  = ["exact-acr-pull"]
      denied   = ["acr-push-delete-import-admin", "role-assignment", "federation", "application-pod-assumption"]
    }
  }
}

resource "azurerm_user_assigned_identity" "jenkins_publisher" {
  name                = "id-${local.stem}-jenkins-publisher"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "jenkins_deployer" {
  name                = "id-${local.stem}-jenkins-deployer"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  tags                = local.tags
}

resource "azurerm_role_assignment" "publisher_exact_acr_push" {
  scope                = azurerm_container_registry.app.id
  role_definition_name = "AcrPush"
  principal_id         = azurerm_user_assigned_identity.jenkins_publisher.principal_id
}

resource "azurerm_role_assignment" "deployer_exact_aks_writer" {
  scope                = azurerm_kubernetes_cluster.app.id
  role_definition_name = "Azure Kubernetes Service RBAC Writer"
  principal_id         = azurerm_user_assigned_identity.jenkins_deployer.principal_id
}

resource "azurerm_role_assignment" "deployer_target_rg_reader" {
  scope                = azurerm_resource_group.app.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.jenkins_deployer.principal_id
}

output "jenkins_delivery_identity_manifest" {
  value = {
    publisher = { resource_id = azurerm_user_assigned_identity.jenkins_publisher.id, client_id = azurerm_user_assigned_identity.jenkins_publisher.client_id, principal_id = azurerm_user_assigned_identity.jenkins_publisher.principal_id }
    deployer  = { resource_id = azurerm_user_assigned_identity.jenkins_deployer.id, client_id = azurerm_user_assigned_identity.jenkins_deployer.client_id, principal_id = azurerm_user_assigned_identity.jenkins_deployer.principal_id }
    validator = null
    ui        = null
    contract  = local.delivery_identity_contract
  }
}
