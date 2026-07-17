from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AZURE = ROOT / "infra/azure"


def source(name: str) -> str:
    return (AZURE / name).read_text()


def test_key_vault_generates_a_rotating_client_auth_certificate_for_csi() -> None:
    cert = source("bff-client-certificate.tf")
    assert 'resource "azurerm_key_vault_certificate" "bff_client"' in cert
    assert 'name = "Self"' in cert
    assert "exportable = true" in cert  # private key is retrievable only through later named CSI authorization
    assert "key_size   = 3072" in cert and 'key_type   = "RSA"' in cert
    assert "reuse_key  = false" in cert
    assert 'content_type = "application/x-pem-file"' in cert
    assert 'extended_key_usage = ["1.3.6.1.5.5.7.3.2"]' in cert
    assert 'key_usage          = ["digitalSignature"]' in cert
    assert "validity_in_months = 3" in cert
    assert 'action_type = "AutoRenew"' in cert and "days_before_expiry = 30" in cert
    assert "prevent_destroy = true" in cert


def test_rotation_policy_has_exact_normal_partial_rollback_and_emergency_bounds() -> None:
    policy = source("bff-certificate-rotation.tf")
    assert 'candidate_available_before_retirement = "PT24H"' in policy
    assert 'retirement_deadline_after_activation  = "PT48H"' in policy
    assert 'retry_window              = "PT24H"' in policy
    assert "every_current_replica = true" in policy
    for probe in (
        "certificate-parse",
        "public-private-key-match",
        "thumbprint-version-match",
        "expiry",
        "fresh-sign-in-callback",
        "existing-session-refresh",
        "delegated-core-token",
        "health-app-token",
    ):
        assert f'"{probe}"' in policy
    assert "nonconverged_replica_ready = false" in policy
    assert "quarantine_candidate      = true" in policy
    assert "explicit_operator_release = true" in policy
    assert "retire_prior              = false" in policy
    assert "require_every_replica_probe = true" in policy
    assert "revoke_compromised_immediately = true" in policy
    assert "unsafe_fallback_allowed        = false" in policy
    assert "preserve_saved_core_records    = true" in policy


def test_outputs_are_versioned_public_metadata_only() -> None:
    cert = source("bff-client-certificate.tf")
    policy = source("bff-certificate-rotation.tf")
    assert 'output "bff_client_certificate"' in cert
    assert "certificate_version" in cert and "thumbprint" in cert
    assert 'private_key_location       = "key-vault-csi-only"' in cert
    assert 'output "bff_client_certificate_rotation_policy"' in policy
    assert "version_identifiers_only = true" in policy
    assert "private_key_material     = false" in policy
    combined = (cert + policy).lower()
    for forbidden in ("private_key_pem", "pfx_password", "certificate_data_base64", "secret_value"):
        assert forbidden not in combined
