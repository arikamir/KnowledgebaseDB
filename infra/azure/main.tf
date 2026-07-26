locals {
  stem = "${var.prefix}-${var.environment}"
  # Keep AKS API access in the infrastructure contract. In the technical PoC
  # the already-reviewed operator CIDRs are reused; formal environments must
  # provide their own reviewed control-plane CIDRs explicitly.
  aks_api_server_authorized_ip_ranges = var.aks_api_server_authorized_ip_ranges != null ? var.aks_api_server_authorized_ip_ranges : (var.technical_poc_mode ? var.poc_operator_source_cidrs : null)
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
    name           = "system"
    vm_size        = var.node_vm_size
    node_count     = var.node_count
    vnet_subnet_id = azurerm_subnet.aks.id

    upgrade_settings {
      max_surge = "10%"
    }
  }

  identity { type = "SystemAssigned" }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.app.id
  }

  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }

  role_based_access_control_enabled = true
  api_server_access_profile {
    authorized_ip_ranges = local.aks_api_server_authorized_ip_ranges
  }
  network_profile {
    network_plugin = "azure"
    network_policy = "azure"
    outbound_type  = "loadBalancer"
  }
  lifecycle {
    precondition {
      condition     = var.technical_poc_mode || try(length(var.aks_api_server_authorized_ip_ranges), 0) > 0
      error_message = "Formal environments must provide at least one reviewed AKS API authorized CIDR."
    }
  }
  tags = local.tags
}

resource "azurerm_role_assignment" "kubelet_exact_acr_pull" {
  scope                = azurerm_container_registry.app.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.app.kubelet_identity[0].object_id
}
