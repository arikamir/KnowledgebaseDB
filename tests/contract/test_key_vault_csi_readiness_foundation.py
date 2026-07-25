from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "deploy/k8s/base"


def load(path: str) -> dict:
    return yaml.safe_load((BASE / path).read_text())


def test_bff_mounts_exact_versioned_client_certificate_and_public_core_trust() -> None:
    provider = (BASE / "bff/secret-provider-class.yaml").read_text()
    deployment = load("bff/deployment.yaml")
    assert "${BFF_WORKLOAD_CLIENT_ID}" in provider
    assert "objectName: bff-confidential-client" in provider
    assert "objectType: secret" in provider
    assert 'objectVersion: "${BFF_CLIENT_CERTIFICATE_VERSION}"' in provider
    assert "objectAlias: bff-client.pem" in provider
    assert "objectName: private-core-server" in provider
    assert "objectType: cert" in provider
    assert "objectAlias: core-ca.pem" in provider
    pod = deployment["spec"]["template"]["spec"]
    container = pod["containers"][0]
    assert any(volume.get("csi", {}).get("driver") == "secrets-store.csi.k8s.io" for volume in pod["volumes"])
    assert any(mount["mountPath"] == "/var/run/secrets/career-agent" and mount["readOnly"] for mount in container["volumeMounts"])


def test_core_mounts_exact_versioned_private_tls_pair_and_public_chain() -> None:
    provider = (BASE / "core/secret-provider-class.yaml").read_text()
    deployment = load("core/deployment.yaml")
    config = load("core/configmap.yaml")["data"]
    assert "${CORE_WORKLOAD_CLIENT_ID}" in provider
    assert provider.count("objectName: private-core-server") == 2
    assert "objectType: secret" in provider and "objectAlias: core-tls.pem" in provider
    assert "objectType: cert" in provider and "objectAlias: core-chain.pem" in provider
    assert provider.count('objectVersion: "${PRIVATE_CORE_CERTIFICATE_VERSION}"') == 2
    assert config["CORE_TLS_CERTIFICATE_VERSION"] == "${PRIVATE_CORE_CERTIFICATE_VERSION}"
    assert config["CORE_TLS_EXPECTED_SANS"] == "core.${PRIVATE_CORE_DNS_ZONE_NAME},core.career-agent.svc,core.career-agent.svc.cluster.local"
    assert config["CORE_TLS_EXPECTED_ISSUER"] == "${PRIVATE_CORE_CERTIFICATE_ISSUER_NAME}"


def test_readiness_fails_closed_without_plaintext_environment_or_kubernetes_secret_fallback() -> None:
    for service in ("bff", "core"):
        deployment_text = (BASE / f"{service}/deployment.yaml").read_text()
        provider_text = (BASE / f"{service}/secret-provider-class.yaml").read_text()
        deployment = load(f"{service}/deployment.yaml")
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        env = {item["name"]: item["value"] for item in container["env"]}
        assert container["readinessProbe"]["httpGet"]["path"] == "/health/ready"
        assert env["KEY_MATERIAL_FAILURE_CODE"] == "KEY_MATERIAL_UNAVAILABLE"
        assert env["KEY_MATERIAL_FALLBACK"] == "disabled"
        assert "secretObjects:" not in provider_text
        assert "secretKeyRef" not in deployment_text
        assert "privateKey" not in deployment_text and "certificateData" not in deployment_text
    bff_health = (ROOT / "bff/src/routes/health.ts").read_text()
    core_health = (ROOT / "src/api/routes/health.py").read_text()
    assert "mountedClientCertificateReady" in bff_health
    assert "certificatePublicKey.equals(privatePublicKey)" in bff_health
    assert "READINESS_REQUIRED_DEPENDENCIES" in bff_health and "!(name in checks)" in bff_health
    assert "MountedPemMaterialProbe" in core_health
    assert "SubjectPublicKeyInfo" in core_health and "CORE_TLS_EXPECTED_SANS" in core_health
    assert 'name not in checks' in core_health


def test_named_secret_rbac_allows_only_the_owning_workload_and_rotation_identity_still_cannot_export() -> None:
    bff = (ROOT / "infra/azure/bff-client-certificate.tf").read_text()
    core = (ROOT / "infra/azure/core-machine-certificate.tf").read_text()
    certs = (ROOT / "infra/azure/gateway-certificates.tf").read_text()
    rotation = core.split('resource "azurerm_role_definition" "gateway_certificate_versions"', 1)[1].split('resource "azurerm_role_assignment" "gateway_certificate_versions"', 1)[0]
    assert 'role_definition_name = "Key Vault Secrets User"' in bff
    assert 'workload["bff"].principal_id' in bff
    assert '/secrets/${azurerm_key_vault_certificate.bff_client.name}' in bff
    assert 'role_definition_name = "Key Vault Secrets User"' in core
    assert 'workload["core"].principal_id' in core
    assert '/secrets/${azurerm_key_vault_certificate.private_core.name}' in core
    assert "Microsoft.KeyVault/vaults/secrets/getSecret/action" in rotation
    assert 'private_key_access = "exact-core-csi-only"' in certs
