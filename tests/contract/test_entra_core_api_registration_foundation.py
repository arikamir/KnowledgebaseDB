from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TERRAFORM = ROOT / "infra/azure/entra-core-api-registration.tf"


def source() -> str:
    return TERRAFORM.read_text()


def test_core_is_a_single_tenant_protected_api_with_one_exact_audience() -> None:
    text = source()
    assert 'resource "azuread_application" "core_api"' in text
    assert 'core_api_audience       = "api://${var.tenant_id}/${var.prefix}-${var.environment}-career-agent-core"' in text
    assert "identifier_uris  = [local.core_api_audience]" in text
    assert 'sign_in_audience = "AzureADMyOrg"' in text
    assert "fallback_public_client_enabled = false" in text
    assert "requested_access_token_version = 2" in text
    assert "web {" not in text and "public_client {" not in text


def test_core_exposes_only_the_exact_delegated_employee_scope_at_this_checkpoint() -> None:
    text = source()
    assert text.count("oauth2_permission_scope {") == 1
    assert 'core_employee_scope     = "CareerAgent.Access"' in text
    assert 'type                       = "User"' in text
    assert "value                      = local.core_employee_scope" in text
    assert "core_employee_scope_uri = \"${local.core_api_audience}/${local.core_employee_scope}\"" in text
    assert "app_role {" not in text
    for prohibited in ("LearningBff.Session.Revoke", "User.Read.All", "client_secret", "password"):
        assert prohibited not in text


def test_core_service_principal_and_outputs_are_locked_and_nonsecret() -> None:
    text = source()
    assert 'resource "azuread_service_principal" "core_api"' in text
    assert "app_role_assignment_required = true" in text
    assert text.count("prevent_destroy = true") == 2
    assert 'output "entra_core_api_registration"' in text
    for field in (
        "application_object_id",
        "client_id",
        "service_principal_object_id",
        "audience",
        "employee_scope_value",
        "employee_scope_id",
        "employee_scope_uri",
        "import_application_command",
        "import_principal_command",
    ):
        assert field in text
    for secret_field in ("client_secret", "private_key", "certificate_value", "password"):
        assert secret_field not in text.lower()
