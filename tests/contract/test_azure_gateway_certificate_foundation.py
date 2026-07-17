from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AZURE = ROOT / "infra/azure"


def source(name: str) -> str:
    return (AZURE / name).read_text()


def test_server_certificates_are_nonexportable_issuer_backed_and_exact_san() -> None:
    certificates = source("gateway-certificates.tf")
    assert certificates.count("      exportable = false") == 2
    assert "var.public_certificate_issuer_name" in certificates
    assert "var.private_core_certificate_issuer_name" in certificates
    assert certificates.count('key_type   = "RSA"') == 2
    assert '"core.career-agent.svc"' in certificates
    assert '"core.career-agent.svc.cluster.local"' in certificates
    assert "local.public_gateway_hostname" in certificates
    variables = source("variables.tf")
    assert '!contains(["Self", "Unknown", ""], var.public_certificate_issuer_name)' in variables
    assert '!contains(["Self", "Unknown", ""], var.private_core_certificate_issuer_name)' in variables


def test_private_ca_key_and_version_lifecycle_metadata_are_key_vault_only() -> None:
    certificates = source("gateway-certificates.tf")
    assert 'resource "azurerm_key_vault_key" "private_core_ca"' in certificates
    assert 'key_opts     = ["sign", "verify"]' in certificates
    assert "resource_versionless_id" in certificates
    for field in ("active_version", "candidate_version", "retired_versions", "minimum_overlap", "retirement_deadline"):
        assert certificates.count(field) >= 2
    assert 'minimum_overlap     = "PT24H"' in certificates
    assert 'retirement_deadline = "PT48H"' in certificates
    assert 'distribution           = "key-vault-csi-public-x509-chain-only"' in certificates
    assert "source_certificate_id" in certificates
    lowered = certificates.lower()
    assert "private_key_pem" not in lowered and "pfx_password" not in lowered


def test_rotation_identity_is_scoped_to_named_certificates_and_dns_records() -> None:
    roles = source("core-machine-certificate.tf")
    allowed = roles.split("data_actions = [", 1)[1].split("]", 1)[0]
    for operation in ("certificates/read", "certificates/create/action", "certificates/import/action", "certificates/update/action"):
        assert operation in allowed
    assert "secrets/" not in allowed and "certificates/delete" not in allowed
    assert '"${azurerm_key_vault.app.id}/certificates/${azurerm_key_vault_certificate.public_gateway.name}"' in roles
    assert '"${azurerm_key_vault.app.id}/certificates/${azurerm_key_vault_certificate.private_core.name}"' in roles
    for exact_record in ("azurerm_dns_cname_record.browser.id", "azurerm_dns_txt_record.browser_certificate_validation.id", "azurerm_private_dns_a_record.core.id"):
        assert exact_record in roles
    for denial in ("dnsZones/delete", "privateDnsZones/delete", "Microsoft.Authorization/*"):
        assert denial in roles


def test_dns_urls_and_network_controls_are_authoritative_and_private_core_is_not_public() -> None:
    public_dns = source("gateway-dns.tf")
    private_dns = source("private-dns.tf")
    agc = source("application-gateway-for-containers.tf")
    outputs = source("outputs.tf")
    assert "azurerm_application_load_balancer_frontend.public.fully_qualified_domain_name" in public_dns
    assert 'resource "azurerm_private_dns_zone" "core"' in private_dns
    assert 'resource "azurerm_private_dns_a_record" "core"' in private_dns
    assert "azurerm_public_ip" not in private_dns
    assert 'name                       = "allow-approved-public-https"' in agc
    assert "var.browser_gateway_source_cidrs" in agc
    assert 'source_address_prefix      = "AzureLoadBalancer"' in agc
    assert "https://${local.public_gateway_hostname}/" in outputs
    assert "https://${local.private_core_hostname}/" in outputs


def test_url_helper_reads_only_the_nonsecret_authoritative_output() -> None:
    helper = (ROOT / "scripts/azure/get-application-url.sh").read_text()
    assert "output -json gateway_certificate_dns_bootstrap" in helper
    assert ".browser_url" in helper
    assert "https://" in helper
    for forbidden in ("kubectl", "Ingress", "kubeconfig", "secret", "tfstate"):
        assert forbidden.lower() not in helper.lower()
