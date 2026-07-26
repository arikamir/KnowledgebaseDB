from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AZURE = ROOT / "infra/azure"


def source(name: str) -> str:
    return (AZURE / name).read_text()


def test_remote_state_and_both_providers_are_explicitly_locked() -> None:
    backend = source("backend.tf")
    versions = source("versions.tf")
    providers = source("providers.tf")
    lock = source(".terraform.lock.hcl")

    assert 'backend "azurerm"' in backend
    assert "use_azuread_auth = true" in backend
    assert "use_oidc         = false" in backend
    assert 'provider "azurerm"' in providers and 'provider "azuread"' in providers
    assert "tenant_id" in providers and "subscription_id" in providers
    assert 'source  = "hashicorp/azurerm"' in versions
    assert 'source  = "hashicorp/azuread"' in versions
    assert 'provider "registry.terraform.io/hashicorp/azurerm"' in lock
    assert 'provider "registry.terraform.io/hashicorp/azuread"' in lock
    assert "storage_account_name" not in backend and "access_key" not in backend


def test_managed_dependencies_are_private_entra_only_and_monitored() -> None:
    key_vault = source("key-vault.tf")
    redis = source("redis.tf")
    postgresql = source("postgresql.tf")
    network = source("private-networking.tf")
    monitoring = source("monitoring.tf")

    assert "rbac_authorization_enabled    = true" in key_vault
    assert "purge_protection_enabled      = true" in key_vault
    assert "public_network_access_enabled = var.technical_poc_mode" in key_vault
    assert 'default_action = "Deny"' in key_vault
    assert "ip_rules       = var.technical_poc_mode ? var.poc_operator_source_cidrs : []" in key_vault
    assert 'public_network_access     = "Disabled"' in redis
    assert "access_keys_authentication_enabled = false" in redis
    assert 'client_protocol                    = "Encrypted"' in redis
    assert 'resource "azurerm_managed_redis_access_policy_assignment" "bff"' in redis
    assert 'azurerm_user_assigned_identity.workload["bff"]' in redis
    assert "active_directory_auth_enabled = true" in postgresql
    assert "password_auth_enabled         = false" in postgresql
    assert "public_network_access_enabled = false" in postgresql
    assert "delegated_subnet_id" in postgresql and "private_dns_zone_id" in postgresql
    assert 'principal_type      = "Group"' in postgresql
    for zone in ("privatelink.vaultcore.azure.net", "privatelink.redis.azure.net", "private.postgres.database.azure.com"):
        assert zone in network
    for dependency in ("azurerm_key_vault.app.id", "azurerm_managed_redis.bff.id", "azurerm_postgresql_flexible_server.core.id"):
        assert dependency in monitoring
    assert 'for_each = each.key == "redis" ? [] : ["allLogs"]' in monitoring
    assert "category_group = enabled_log.value" in monitoring


def test_aks_control_plane_access_is_terraform_managed() -> None:
    main = source("main.tf")
    variables = source("variables.tf")
    outputs = source("outputs.tf")

    assert "api_server_access_profile" in main
    assert "authorized_ip_ranges = local.aks_api_server_authorized_ip_ranges" in main
    assert "var.aks_api_server_authorized_ip_ranges" in main
    assert "var.poc_operator_source_cidrs" in main
    assert "Formal environments must provide at least one reviewed AKS API authorized CIDR." in main
    assert 'variable "aks_api_server_authorized_ip_ranges"' in variables
    assert "can(cidrnetmask(cidr))" in variables
    assert "aks_api_server_fqdn" in outputs
    assert "aks_api_server_authorized_ip_ranges" in outputs


def test_bff_key_ring_is_versioned_and_contains_no_key_material() -> None:
    encryption = source("bff-session-encryption.tf")
    assert 'name         = "bff-session-encryption"' in encryption
    assert "rotation_policy" in encryption
    assert "active_version" in encryption and "decrypt_only_versions" in encryption
    assert "revoke-indexed-sessions-before-disable" in encryption
    assert 'role_definition_name = "Key Vault Crypto User"' in encryption
    assert "resource_versionless_id" in encryption
    lowered = encryption.lower()
    assert "private_key" not in lowered and "key_value" not in lowered


def test_data_plane_contract_is_exact_and_mutually_denied() -> None:
    contract = source("data-plane-rbac.tf")
    bootstrap = (ROOT / "scripts/azure/bootstrap-data-principals.sh").read_text()

    for role in ("core-dml", "lifecycle", "retention", "lab-validation", "migrator"):
        assert role in contract
    for required_boundary in (
        "application-schema-select-insert-update-delete",
        "unclaimed-retention-insert-narrow-update",
        "retention-select-delete-claim-complete",
        "execute-audited-claim-due",
        "direct-learning-row-read",
        "validation-timestamp-status-failure-counter-safe-error-update",
        "migration-ddl",
        "runtime-application-dml",
    ):
        assert required_boundary in contract
    assert 'workload["bff"].principal_id' in contract
    assert 'workload["core"].principal_id' in contract
    assert 'workload["lifecycle"].principal_id' in contract
    assert 'workload["retention"].principal_id' in contract
    assert 'workload["lab-revalidation"].principal_id' in contract
    assert 'workload["migration"].principal_id' in contract
    assert "DATA_PRINCIPAL_DENIAL_TEST" in bootstrap
    assert "password_auth_enabled" not in contract
    assert "access_keys_authentication_enabled" not in contract
