from pathlib import Path


AZURE = Path(__file__).resolve().parents[2] / "infra/azure"


def tf(name: str) -> str:
    return (AZURE / name).read_text()


def test_bff_confidential_client_has_exact_callback_logout_and_core_access_only():
    bff = tf("entra-bff-registration.tf")
    assert 'sign_in_audience = "AzureADMyOrg"' in bff
    assert "fallback_public_client_enabled = false" in bff
    assert 'redirect_uris = [local.bff_redirect_uri]' in bff
    assert 'bff_redirect_uri   = "${local.bff_browser_origin}/bff/v1/auth/callback"' in bff
    assert 'logout_url    = local.bff_logout_uri' in bff
    assert bff.count('type = "Scope"') == 1
    assert 'oauth2_permission_scope_ids[local.core_employee_scope]' in bff
    assert bff.count('type = "Role"') == 1
    assert 'app_role_ids["CareerAgent.Health.Read"]' in bff
    for forbidden in ("client_secret", "password", "CareerAgent.Progress.Write", "CareerAgent.Roadmap.Generate"):
        assert forbidden not in bff


def test_core_is_protected_v2_api_with_one_delegated_scope_and_application_roles():
    core = tf("entra-core-api-registration.tf")
    roles = tf("entra-app-roles.tf")
    assert 'identifier_uris  = [local.core_api_audience]' in core
    assert "requested_access_token_version = 2" in core
    assert core.count("oauth2_permission_scope {") == 1
    assert 'core_employee_scope     = "CareerAgent.Access"' in core
    assert 'type                       = "User"' in core
    assert 'allowed_member_types = ["Application"]' in core
    assert 'resource "azuread_app_role_assignment" "bff_core_health"' in roles
    assert 'app_role_id         = azuread_application.core_api.app_role_ids["CareerAgent.Health.Read"]' in roles


def test_lifecycle_has_admin_consented_graph_read_and_only_bff_revocation_role():
    lifecycle = tf("entra-lifecycle-permissions.tf")
    lifecycle_identity = 'azurerm_user_assigned_identity.workload["lifecycle"].principal_id'
    assert lifecycle.count('resource "azuread_app_role_assignment"') == 2
    assert lifecycle.count(lifecycle_identity) == 3
    assert 'app_role_ids["User.Read.All"]' in lifecycle
    assert 'app_role_ids["LearningBff.Session.Revoke"]' in lifecycle
    for forbidden in ("User.ReadWrite.All", "Directory.Read.All", "CareerAgent.Health.Read"):
        assert forbidden not in lifecycle


def test_machine_consumers_receive_declared_core_application_roles_without_delegation():
    machines = tf("entra-machine-registrations.tf")
    variables = tf("variables.tf")
    assert 'resource "azuread_app_role_assignment" "machine_core"' in machines
    assert "app_role_id         = azuread_application.core_api.app_role_ids[each.value.role]" in machines
    assert "for_each = each.value.roles" in machines
    assert "length(setsubtract(consumer.roles" in variables
    assert "CareerAgent.Health.Read" in variables
    for forbidden in ('type = "Scope"', "User.Read.All", "LearningBff.Session.Revoke", "client_secret"):
        assert forbidden not in machines
