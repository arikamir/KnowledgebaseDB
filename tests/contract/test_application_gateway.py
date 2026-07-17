from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
PLATFORM = ROOT / "deploy/k8s/platform/alb-controller"


def load(path): return yaml.safe_load(path.read_text())


def test_alb_controller_chart_crds_workload_identity_and_install_order_are_pinned():
    install = load(PLATFORM / "install-contract.yaml")["data"]
    assert install["chartRepository"] == "oci://mcr.microsoft.com/application-lb/charts/alb-controller"
    assert install["chartVersion"] == "1.11.1" and install["gatewayApiCrdVersion"] == "v1.5.1"
    assert "SHA256}" in install["gatewayApiCrdSha256"] and "SHA256}" in install["chartArtifactSha256"]
    assert install["installOrder"].split(",") == ["gateway-api-crds", "alb-controller", "controller-ready-attestation", "gateway-resources"]
    assert install["liveInstallAllowed"] == "false-before-T194"
    account = load(PLATFORM / "service-account.yaml")
    assert account["metadata"]["name"] == "alb-controller-sa"
    assert account["metadata"]["annotations"]["azure.workload.identity/client-id"] == "${ALB_CONTROLLER_CLIENT_ID}"
    identity = (ROOT / "infra/azure/identity.tf").read_text()
    assert 'alb-controller           = "system:serviceaccount:azure-alb-system:alb-controller-sa"' in identity


def test_alb_identity_has_only_exact_agc_group_and_delegated_subnet_roles_with_full_denial_matrix():
    terraform = (ROOT / "infra/azure/application-gateway-for-containers.tf").read_text()
    assert 'scope                = azurerm_resource_group.app.id' in terraform
    assert 'role_definition_name = "AppGw for Containers Configuration Manager"' in terraform
    assert 'scope                = azurerm_subnet.application_gateway_for_containers.id' in terraform
    assert 'role_definition_name = "Network Contributor"' in terraform
    contract = load(PLATFORM / "authorization-contract.yaml")["data"]
    denied = set(contract["denied"].split(","))
    assert {
        "subscription", "Owner", "Contributor", "role-assignment", "other-vnet", "other-subnet",
        "other-gateway", "identity-mutation", "federation-mutation", "key-vault", "acr", "storage",
        "redis", "postgresql", "unrelated-kubernetes-secret", "alternate-service-account",
    } == denied
    assert contract["bindingCardinality"] == "one-workload-identity-to-one-service-account"


def test_agc_association_frontend_public_tls_dns_and_private_core_boundaries_are_explicit():
    terraform = (ROOT / "infra/azure/application-gateway-for-containers.tf").read_text()
    for resource in (
        'azurerm_application_load_balancer" "app',
        'azurerm_application_load_balancer_subnet_association" "app',
        'azurerm_application_load_balancer_frontend" "public',
    ):
        assert resource in terraform
    assert "Microsoft.ServiceNetworking/trafficControllers" in terraform
    gateway = load(ROOT / "deploy/k8s/overlays/aks-nonprod/gateway.yaml")
    assert gateway["spec"]["listeners"][0]["protocol"] == "HTTPS"
    assert gateway["spec"]["listeners"][0]["tls"]["certificateRefs"][0]["name"] == "public-gateway-tls"
    route = load(ROOT / "deploy/k8s/overlays/aks-nonprod/httproute.yaml")
    backends = {backend["name"] for rule in route["spec"]["rules"] for backend in rule["backendRefs"]}
    assert backends == {"ui", "bff"} and "core" not in backends
    private = load(ROOT / "deploy/k8s/overlays/aks-nonprod/private-machine-service.yaml")
    assert private["metadata"]["annotations"]["service.beta.kubernetes.io/azure-load-balancer-internal"] == "true"


def test_no_legacy_web_app_routing_nginx_controller_ingress_or_public_core_remains():
    manifests = "\n".join(path.read_text() for path in (ROOT / "deploy/k8s").rglob("*.yaml"))
    for forbidden in ("kind: Ingress\n", "webapprouting.kubernetes.azure.com", "ingress-nginx-controller"):
        assert forbidden not in manifests
    assert "web_app_routing" not in (ROOT / "infra/azure/main.tf").read_text()
    assert "core" not in load(ROOT / "deploy/k8s/overlays/aks-nonprod/httproute.yaml")["metadata"]["name"]
