from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text()


def test_poc_mode_is_explicitly_non_release_and_does_not_replace_formal_inputs() -> None:
    variables = read("infra/azure/variables.tf")
    governance = read("infra/azure/poc-governance.tf")
    assert 'variable "technical_poc_mode"' in variables
    assert "This never satisfies T194 or protected delivery" in variables
    assert 'for_each = var.technical_poc_mode ? toset([' in governance
    assert "not separation-of-duties evidence" in governance
    for formal_input in (
        "browser_dns_zone_name",
        "public_certificate_issuer_name",
        "delivery_operators_group_object_id",
        "security_reviewers_group_object_id",
    ):
        assert f'variable "{formal_input}"' in variables


def test_poc_gateway_uses_cert_manager_http01_and_a_kubernetes_tls_secret() -> None:
    overlay = read("deploy/k8s/overlays/aks-poc/kustomization.yaml")
    gateway = read("deploy/k8s/overlays/aks-poc/gateway-http01-patch.yaml")
    issuer = read("deploy/k8s/overlays/aks-poc/cluster-issuer.yaml")
    certificate = read("deploy/k8s/overlays/aks-poc/certificate.yaml")
    assert "../aks-nonprod" in overlay
    assert "http-acme" in gateway and "port: 80" in gateway
    assert "public-gateway-tls" in gateway
    assert "https://acme-v02.api.letsencrypt.org/directory" in issuer
    assert "gatewayHTTPRoute" in issuer
    assert '${ACME_CONTACT_EMAIL}' in issuer
    assert '${PUBLIC_GATEWAY_HOSTNAME}' in certificate
    assert "secretName: public-gateway-tls" in certificate


def test_free_hostname_is_derived_from_the_agc_frontend_ip() -> None:
    helper = read("scripts/azure/resolve-poc-hostname.sh")
    assert "dig +short A" in helper
    assert "career-agent.%s.sslip.io" in helper
    assert "azurerm" not in helper
