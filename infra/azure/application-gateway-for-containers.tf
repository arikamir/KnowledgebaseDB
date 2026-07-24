locals {
  alb_controller_bootstrap = {
    chart                         = "oci://mcr.microsoft.com/application-lb/charts/alb-controller"
    chart_version                 = "1.11.1"
    gateway_api_version           = "v1.5.1"
    minimum_kubernetes_version    = "v1.27"
    namespace                     = "azure-alb-system"
    service_account               = "alb-controller-sa"
    install_owner                 = "platform-operations-t093"
    gateway_creation_prerequisite = "controller-ready-and-attested"
  }
}

resource "azurerm_subnet" "application_gateway_for_containers" {
  name                 = "snet-agc"
  resource_group_name  = azurerm_resource_group.app.name
  virtual_network_name = azurerm_virtual_network.app.name
  address_prefixes     = [var.application_gateway_for_containers_subnet_cidr]

  delegation {
    name = "application-gateway-for-containers"
    service_delegation {
      name    = "Microsoft.ServiceNetworking/trafficControllers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_network_security_group" "application_gateway_for_containers" {
  name                = "nsg-agc-${local.stem}"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  tags                = local.tags

  security_rule {
    name                       = "allow-approved-public-https"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = var.technical_poc_mode ? ["80", "443"] : ["443"]
    source_address_prefixes    = var.browser_gateway_source_cidrs
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "allow-azure-load-balancer"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "AzureLoadBalancer"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "allow-aks-backends"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = var.aks_subnet_cidr
  }

  security_rule {
    name                       = "allow-azure-control-plane"
    priority                   = 110
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "AzureCloud"
  }
}

resource "azurerm_subnet_network_security_group_association" "application_gateway_for_containers" {
  subnet_id                 = azurerm_subnet.application_gateway_for_containers.id
  network_security_group_id = azurerm_network_security_group.application_gateway_for_containers.id
}

resource "azurerm_application_load_balancer" "app" {
  name                = "agc-${local.stem}"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  tags                = local.tags
}

resource "azurerm_application_load_balancer_subnet_association" "app" {
  name                         = "association-${local.stem}"
  application_load_balancer_id = azurerm_application_load_balancer.app.id
  subnet_id                    = azurerm_subnet.application_gateway_for_containers.id
  tags                         = local.tags
  depends_on                   = [azurerm_subnet_network_security_group_association.application_gateway_for_containers]
}

resource "azurerm_application_load_balancer_frontend" "public" {
  name                         = "public-${local.stem}"
  application_load_balancer_id = azurerm_application_load_balancer.app.id
  tags                         = local.tags
}

# Azure authorization is provisioned with the AGC, while T093 alone owns the
# chart, CRDs, service account, Kubernetes RBAC, and install ordering assets.
resource "azurerm_role_assignment" "alb_controller_configuration_manager" {
  scope                = azurerm_resource_group.app.id
  role_definition_name = "AppGw for Containers Configuration Manager"
  principal_id         = azurerm_user_assigned_identity.workload["alb-controller"].principal_id
}

resource "azurerm_role_assignment" "alb_controller_exact_subnet" {
  scope                = azurerm_subnet.application_gateway_for_containers.id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.workload["alb-controller"].principal_id
}

output "application_gateway_for_containers_bootstrap" {
  description = "Non-secret BYO AGC resources and pinned T093 controller-install inputs."
  value = {
    application_gateway_id      = azurerm_application_load_balancer.app.id
    association_id              = azurerm_application_load_balancer_subnet_association.app.id
    frontend_id                 = azurerm_application_load_balancer_frontend.public.id
    frontend_name               = azurerm_application_load_balancer_frontend.public.name
    frontend_fqdn               = azurerm_application_load_balancer_frontend.public.fully_qualified_domain_name
    delegated_subnet_id         = azurerm_subnet.application_gateway_for_containers.id
    controller_identity_id      = azurerm_user_assigned_identity.workload["alb-controller"].id
    controller_client_id        = azurerm_user_assigned_identity.workload["alb-controller"].client_id
    controller_principal_id     = azurerm_user_assigned_identity.workload["alb-controller"].principal_id
    configuration_assignment_id = azurerm_role_assignment.alb_controller_configuration_manager.id
    subnet_assignment_id        = azurerm_role_assignment.alb_controller_exact_subnet.id
    controller                  = local.alb_controller_bootstrap
  }
}
