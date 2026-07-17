from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TERRAFORM = ROOT / "infra/azure/application-gateway-for-containers.tf"


def test_byo_gateway_has_parent_association_frontend_and_dedicated_subnet() -> None:
    source = TERRAFORM.read_text()
    for resource in (
        'resource "azurerm_application_load_balancer" "app"',
        'resource "azurerm_application_load_balancer_subnet_association" "app"',
        'resource "azurerm_application_load_balancer_frontend" "public"',
        'resource "azurerm_subnet" "application_gateway_for_containers"',
    ):
        assert resource in source
    assert 'name    = "Microsoft.ServiceNetworking/trafficControllers"' in source
    assert 'actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]' in source
    assert "application_load_balancer_id = azurerm_application_load_balancer.app.id" in source
    assert "subnet_id                    = azurerm_subnet.application_gateway_for_containers.id" in source
    assert "fully_qualified_domain_name" in source


def test_controller_identity_has_only_documented_gateway_and_subnet_scopes() -> None:
    source = TERRAFORM.read_text()
    identity = 'azurerm_user_assigned_identity.workload["alb-controller"].principal_id'
    assert source.count(identity) == 3  # two assignments plus bootstrap output
    assert 'role_definition_name = "AppGw for Containers Configuration Manager"' in source
    assert 'scope                = azurerm_resource_group.app.id' in source
    assert 'role_definition_name = "Network Contributor"' in source
    assert 'scope                = azurerm_subnet.application_gateway_for_containers.id' in source
    for prohibited in ('role_definition_name = "Owner"', 'role_definition_name = "Contributor"', "subscription_id ="):
        assert prohibited not in source


def test_controller_bootstrap_is_pinned_but_does_not_install_kubernetes_assets() -> None:
    source = TERRAFORM.read_text()
    assert 'chart                         = "oci://mcr.microsoft.com/application-lb/charts/alb-controller"' in source
    assert 'chart_version                 = "1.11.1"' in source
    assert 'gateway_api_version           = "v1.5.1"' in source
    assert 'minimum_kubernetes_version    = "v1.27"' in source
    assert 'namespace                     = "azure-alb-system"' in source
    assert 'service_account               = "alb-controller-sa"' in source
    assert 'install_owner                 = "platform-operations-t093"' in source
    assert "helm_release" not in source and "kubernetes_manifest" not in source


def test_subnet_input_is_fixed_to_the_supported_24_prefix() -> None:
    variables = (ROOT / "infra/azure/variables.tf").read_text()
    assert 'default     = "10.42.18.0/24"' in variables
    assert 'endswith(var.application_gateway_for_containers_subnet_cidr, "/24")' in variables
