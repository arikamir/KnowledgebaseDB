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
    assert text.count("prevent_destroy = true") == 2
    assert 'output "entra_bff_registration"' in text
    for field in (
        "application_object_id",
        "client_id",
        "service_principal_object_id",
        "redirect_uri",
        "logout_uri",
        "internal_api_audience",
        "session_revoke_role_id",
        "import_application_command",
        "import_principal_command",
    ):
        assert field in text
    for secret_field in ("client_secret", "private_key", "certificate_value", "password"):
        assert secret_field not in text.lower()
