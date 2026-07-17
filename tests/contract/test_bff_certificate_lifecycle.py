from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_bff_certificate_is_exportable_only_to_exact_secret_scoped_csi_identity():
    certificate = (ROOT / "infra/azure/bff-client-certificate.tf").read_text()
    registration = (ROOT / "infra/azure/entra-bff-registration.tf").read_text()
    provider = (ROOT / "deploy/k8s/base/bff/secret-provider-class.yaml").read_text()
    assert 'exportable = true' in certificate
    assert 'role_definition_name = "Key Vault Secrets User"' in certificate
    assert '/secrets/${azurerm_key_vault_certificate.bff_client.name}' in certificate
    assert 'workload["bff"].principal_id' in certificate
    assert 'type           = "AsymmetricX509Cert"' in registration
    assert 'value          = azurerm_key_vault_certificate.bff_client.certificate_data' in registration
    for private in ("secret_id", "versionless_secret_id", "private_key", "pfx"):
        assert private not in registration.lower()
    assert 'objectVersion: "${BFF_CLIENT_CERTIFICATE_VERSION}"' in provider
    assert "objectAlias: bff-client.pem" in provider and "secretObjects:" not in provider


def test_rotation_runtime_retains_overlap_evidence_and_rejects_retired_or_revoked_versions():
    coordinator = (ROOT / "bff/src/auth/certificate-rotation.ts").read_text()
    script = (ROOT / "scripts/azure/rotate-bff-client-certificate.sh").read_text()
    assert "24 * 60 * 60 * 1000" in coordinator and "48 * 60 * 60 * 1000" in coordinator
    assert 'previous.status = "retired"' in coordinator
    assert 'state.status = "revoked"' in coordinator
    assert "CERTIFICATE_OVERLAP_TOO_SHORT" in coordinator
    assert "elapsed >= 86400 && elapsed <= 172800" in script
    assert "containsPrivateMaterial:false" in script
    assert "noFallback=true" in script and "clearSessionTokenCaches=true" in script
