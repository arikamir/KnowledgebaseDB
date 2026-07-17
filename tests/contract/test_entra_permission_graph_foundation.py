from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AZURE = ROOT / "infra/azure"


def source(name: str) -> str:
    return (AZURE / name).read_text()


def test_core_publishes_only_the_four_exact_application_roles() -> None:
    roles = source("entra-app-roles.tf")
    expected = {
        "CareerAgent.Roadmap.Generate",
        "CareerAgent.Guidance.Read",
        "CareerAgent.Progress.Write",
        "CareerAgent.Health.Read",
    }
    for role in expected:
        assert roles.count(f'"{role}"') >= 1
    assert roles.count("allowed_principal") == 1
    core = source("entra-core-api-registration.tf")
    assert 'dynamic "app_role"' in core
    assert 'allowed_member_types = ["Application"]' in core
    assert "for_each = local.core_application_roles" in core


def test_bff_receives_only_employee_delegation_and_health_application_role() -> None:
    bff = source("entra-bff-registration.tf")
    roles = source("entra-app-roles.tf")
    assert bff.count('type = "Scope"') == 1
    assert bff.count('type = "Role"') == 1
    assert 'oauth2_permission_scope_ids[local.core_employee_scope]' in bff
    assert 'app_role_ids["CareerAgent.Health.Read"]' in bff
    assert 'resource "azuread_service_principal_delegated_permission_grant" "bff_core_employee"' in roles
    assert "claim_values                         = [local.core_employee_scope]" in roles
    assert 'resource "azuread_app_role_assignment" "bff_core_health"' in roles
    for forbidden in ("Roadmap.Generate", "Guidance.Read", "Progress.Write"):
        assert forbidden not in bff


def test_lifecycle_has_only_admin_consented_user_read_and_session_revoke_roles() -> None:
    text = source("entra-lifecycle-permissions.tf")
    identity = 'azurerm_user_assigned_identity.workload["lifecycle"].principal_id'
    assert text.count(identity) == 3
    assert 'app_role_ids["User.Read.All"]' in text
    assert 'app_role_ids["LearningBff.Session.Revoke"]' in text
    assert text.count('resource "azuread_app_role_assignment"') == 2
    for prohibited in ("Directory.Read.All", "User.ReadWrite.All", "Application.ReadWrite.All"):
        assert prohibited not in text


def test_machine_inventory_is_required_and_each_assignment_is_role_subset_scoped() -> None:
    variables = source("variables.tf")
    machines = source("entra-machine-registrations.tf")
    assert 'variable "approved_machine_consumers"' in variables
    assert "length(var.approved_machine_consumers) > 0" in variables
    assert "setsubtract(consumer.roles" in variables
    assert 'resource "azuread_application" "machine"' in machines
    assert 'resource "azuread_service_principal" "machine"' in machines
    assert 'resource "azuread_app_role_assignment" "machine_core"' in machines
    assert "for_each = local.machine_role_assignments" in machines
    assert "for_each = each.value.roles" in machines
    assert "app_role_assignment_required = true" in machines
    assert "fallback_public_client_enabled = false" in machines
    for forbidden in ("password", "client_secret", "User.Read.All", "LearningBff.Session.Revoke"):
        assert forbidden not in machines.lower()
