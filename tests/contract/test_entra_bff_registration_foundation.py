from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TERRAFORM = ROOT / "infra/azure/entra-bff-registration.tf"


def source() -> str:
    return TERRAFORM.read_text()


def test_bff_is_a_single_tenant_confidential_web_client_with_exact_uris() -> None:
    text = source()
    assert 'resource "azuread_application" "bff"' in text
    assert 'sign_in_audience = "AzureADMyOrg"' in text
    assert "fallback_public_client_enabled = false" in text
    assert 'bff_redirect_uri   = "${local.bff_browser_origin}/bff/v1/auth/callback"' in text
    assert 'bff_logout_uri     = "${local.bff_browser_origin}/bff/v1/auth/logout"' in text
    assert "redirect_uris = [local.bff_redirect_uri]" in text
    assert "logout_url    = local.bff_logout_uri" in text
    assert "access_token_issuance_enabled = false" in text
    assert "id_token_issuance_enabled     = false" in text
    assert "password" not in text.lower() and "client_secret" not in text.lower()


def test_bff_internal_api_exposes_only_lifecycle_session_revocation() -> None:
    text = source()
    assert 'bff_api_audience   = "api://${var.tenant_id}/${var.prefix}-${var.environment}-learning-bff"' in text
    assert text.count("app_role {") == 1
    assert 'allowed_member_types = ["Application"]' in text
    assert 'value                = "LearningBff.Session.Revoke"' in text
    assert "requested_access_token_version = 2" in text
    assert text.count('type = "Scope"') == 1
    assert text.count('type = "Role"') == 1
    assert 'app_role_ids["CareerAgent.Health.Read"]' in text
    for prohibited in ("CareerAgent.Roadmap.Generate", "CareerAgent.Guidance.Read", "CareerAgent.Progress.Write", "User.Read.All"):
        assert prohibited not in text


def test_registration_has_a_locked_service_principal_and_nonsecret_importable_output() -> None:
    text = source()
    assert 'resource "azuread_service_principal" "bff"' in text
    assert "app_role_assignment_required = true" in text
    assert text.count("prevent_destroy = true") == 3
    assert 'output "entra_bff_registration"' in text
    for field in (
        "application_object_id",
        "client_id",
        "service_principal_object_id",
        "redirect_uri",
        "logout_uri",
        "internal_api_audience",
        "session_revoke_role_id",
        "certificate_registration_id",
        "certificate_thumbprint",
        "certificate_version",
        "import_application_command",
        "import_principal_command",
    ):
        assert field in text
    for secret_field in ("client_secret", "private_key", "certificate_value", "password"):
        assert secret_field not in text.lower()


def test_entra_registration_receives_only_public_x509_certificate_material() -> None:
    text = source()
    assert 'resource "azuread_application_certificate" "bff_active"' in text
    assert 'type           = "AsymmetricX509Cert"' in text
    assert 'encoding       = "hex"' in text
    assert "value          = azurerm_key_vault_certificate.bff_client.certificate_data" in text
    assert "certificate_attribute[0].not_before" in text
    assert "certificate_attribute[0].expires" in text
    assert 'certificate_material        = "public-x509-only"' in text
    assert "prevent_destroy = true" in text
    assert "ignore_changes  = [value, start_date, end_date]" in text
    for forbidden in ("secret_id", "versionless_secret_id", "certificate_data_base64", "private_key", "pfx"):
        assert forbidden not in text.lower()
