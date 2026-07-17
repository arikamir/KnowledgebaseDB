locals {
  stem = "${var.prefix}-${var.environment}"
  tags = {
    application = "devops-career-agent"
    environment = var.environment
    managed-by  = "terraform"
  }
}

resource "azurerm_resource_group" "app" {
  name     = "rg-${local.stem}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_container_registry" "app" {
  name                = replace("acr${var.prefix}${var.environment}", "-", "")
  resource_group_name = azurerm_resource_group.app.name
  location            = azurerm_resource_group.app.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}

resource "azurerm_log_analytics_workspace" "app" {
  name                = "log-${local.stem}"
  resource_group_name = azurerm_resource_group.app.name
  location            = azurerm_resource_group.app.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_kubernetes_cluster" "app" {
  name                = "aks-${local.stem}"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  dns_prefix          = local.stem

  default_node_pool {
    name       = "system"
    vm_size    = var.node_vm_size
    node_count = var.node_count
  }

  identity { type = "SystemAssigned" }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.app.id
  }

  role_based_access_control_enabled = true
  tags                              = local.tags
}

resource "azurerm_role_assignment" "kubelet_exact_acr_pull" {
  scope                = azurerm_container_registry.app.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.app.kubelet_identity[0].object_id
}
