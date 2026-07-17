from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLOUD_POLICY = ROOT / "config/jenkins-cloud-credential-policy-v1.json"
IDENTITY_POLICY = ROOT / "config/jenkins-aci-identity-policy-v1.json"
IDENTITIES_TF = ROOT / "infra/azure/jenkins-agent-identities.tf"
CONFIGURE_VALIDATOR = ROOT / "scripts/jenkins/configure-validator-agent.groovy"
CONFIGURE_DELIVERY = ROOT / "scripts/jenkins/configure-publisher-deployer-agents.groovy"
VERIFY_CLOUD = ROOT / "scripts/jenkins/verify-cloud-credential.sh"
VERIFY_BINDING = ROOT / "scripts/jenkins/verify-aci-identity-binding.sh"
DOCS = ROOT / "docs/jenkins-azure-cloud.md"


def test_cloud_azure_provisioner_is_expiring_and_confined_to_aci_lifecycle() -> None:
    policy = json.loads(CLOUD_POLICY.read_text())
    assert policy["cloud"] == "azure"
    assert policy["minimumValidDays"] == 30
    assert policy["requiredAssignments"] == [
        {"roleDefinitionName": "Jenkins ACI Provisioner", "scopeSource": "resourceGroupId"},
        {"roleDefinitionName": "Managed Identity Operator", "scopeSource": "identityResourceIds"},
    ]
    assert {
        "AcrPush", "AcrDelete", "Contributor", "Owner",
        "Azure Kubernetes Service Contributor Role",
        "Azure Kubernetes Service RBAC Cluster Admin",
        "Storage Blob Data Contributor", "Key Vault Secrets User",
    } <= set(policy["forbiddenRoleNames"])
    verifier = VERIFY_CLOUD.read_text()
    assert 'emit_failure "minimum-validity"' in verifier
    assert 'emit_failure "role-assignment-drift"' in verifier
    assert 'emit_failure "identity-scope-invalid"' in verifier


def test_validator_is_identityless_and_provisioning_failure_has_no_fallback() -> None:
    source = CONFIGURE_VALIDATOR.read_text()
    docs = DOCS.read_text()
    assert 'getByName("azure")' in source
    assert ".withEnvVars([])" in source
    assert "managedIdentity" not in source and "userAssigned" not in source
    assert "agent none" in docs
    assert "No controller, built-in, or local-agent fallback" in docs
    assert "provisioning or validation fails" in docs


def test_publisher_and_deployer_have_distinct_exact_uamis_and_no_terraform_surface() -> None:
    policy = json.loads(IDENTITY_POLICY.read_text())
    assert policy["templates"]["publisher"]["identitySource"] == "identities.publisher"
    assert policy["templates"]["deployer"]["identitySource"] == "identities.deployer"
    assert policy["templates"]["validator"]["identitySource"] is None
    assert policy["controllerOrLocalFallback"] is False
    assert "terraform" not in {
        stage for template in policy["templates"].values() for stage in template["allowedStages"]
    }
    source = CONFIGURE_DELIVERY.read_text()
    assert 'getByName("azure")' in source
    assert "manifest.identities.publisher" in source
    assert "manifest.identities.deployer" in source
    assert ".withUseSystemAssignedIdentity(false)" in source
    assert ".withUserAssignedIdentities([identity])" in source
    assert "PLATFORM_BOOTSTRAP_MANIFEST" in source


def test_terraform_grants_publisher_acr_only_and_deployer_aks_plus_target_rg_reader() -> None:
    source = IDENTITIES_TF.read_text()
    assert 'role_definition_name = "AcrPush"' in source
    assert "scope                = azurerm_container_registry.app.id" in source
    assert 'role_definition_name = "Azure Kubernetes Service RBAC Writer"' in source
    assert "scope                = azurerm_kubernetes_cluster.app.id" in source
    assert 'role_definition_name = "Reader"' in source
    assert "scope                = azurerm_resource_group.app.id" in source
    for denied in (
        "terraform-state", "key-vault-secret", "redis-data", "postgresql-data",
        "acr-push-delete-import-admin",
    ):
        assert denied in source


def test_binding_gate_rejects_wrong_template_uami_subscription_and_cross_role_surfaces() -> None:
    policy = json.loads(IDENTITY_POLICY.read_text())
    assert set(policy["requiredDenials"]) == {
        "terraform-state-read", "key-vault-secret-read", "acr-content-read",
        "redis-data-access", "postgresql-data-access",
    }
    assert set(policy["crossIdentityDenials"]) == {
        "publisher-as-deployer", "deployer-as-publisher", "application-workload",
        "alb-controller", "gateway-certificate-dns", "aks-kubelet",
    }
    verifier = VERIFY_BINDING.read_text()
    for required in (
        "missing, swapped, additional, or system-assigned identity",
        "running ACI identity does not match",
        "unauthorized template, token, or stage",
        "role assignment or required denial evidence drifted",
    ):
        assert required in verifier
    assert 'startswith("/subscriptions/")' in verifier

