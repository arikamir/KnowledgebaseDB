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
    kubelet = {
      identity = "aks-kubelet-non-federatable"
      allowed  = ["exact-acr-pull"]
      denied   = ["acr-push-delete-import-admin", "role-assignment", "federation", "application-pod-assumption"]
    }
  }
}

moved {
  from = azurerm_user_assigned_identity.jenkins_publisher
  to   = azurerm_user_assigned_identity.github_actions_publisher
}

resource "azurerm_user_assigned_identity" "github_actions_publisher" {
  name                = "id-${local.stem}-github-actions-publisher"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  tags                = local.tags
  lifecycle {
    # Preserve the current cloud identity name after the Terraform address
    # migration; new environments use the GitHub Actions name above.
    ignore_changes = [name]
  }
}

resource "azurerm_role_assignment" "publisher_exact_acr_push" {
  scope                = azurerm_container_registry.app.id
  role_definition_name = "AcrPush"
  principal_id         = azurerm_user_assigned_identity.github_actions_publisher.principal_id
}

# The publisher uses a protected GitHub environment and can push images to ACR.
# Application deployment remains GitOps-owned and receives no direct AKS identity.
resource "azurerm_federated_identity_credential" "github_actions_publisher" {
  name                = "github-actions-publisher-${var.environment}"
  resource_group_name = azurerm_resource_group.app.name
  parent_id           = azurerm_user_assigned_identity.github_actions_publisher.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:${split("/", var.github_repository)[0]}@${var.github_repository_owner_id}/${split("/", var.github_repository)[1]}@${var.github_repository_id}:environment:${var.github_actions_environment}-publisher"
}

output "github_actions_delivery_identity_manifest" {
  description = "Client IDs and OIDC subjects required by the GitHub Actions environments."
  value = {
    publisher = {
      client_id = azurerm_user_assigned_identity.github_actions_publisher.client_id
      subject   = azurerm_federated_identity_credential.github_actions_publisher.subject
    }
    issuer   = "https://token.actions.githubusercontent.com"
    audience = "api://AzureADTokenExchange"
  }
}
