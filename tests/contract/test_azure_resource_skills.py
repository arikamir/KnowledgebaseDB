from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
INFRA = ROOT / "infra/azure"
PROVISION = ROOT / ".agents/skills/provision-azure-app-resources"
TEARDOWN = ROOT / ".agents/skills/teardown-azure-app-resources"
WORKLOAD_IDENTITIES = (INFRA / "identity.tf").read_text()
DELIVERY_IDENTITIES = (INFRA / "jenkins-agent-identities.tf").read_text()
IDENTITIES = WORKLOAD_IDENTITIES + DELIVERY_IDENTITIES
ASSET_IDENTITIES = (PROVISION / "assets/terraform/jenkins-agent-identities.tf").read_text()

WORKLOADS = {
    "bff", "core", "lifecycle", "retention", "lab-revalidation", "migration",
    "evidence-hold-reconciler", "alb-controller", "gateway-certificate-dns",
}


def test_aks_uses_oidc_workload_identity_and_no_legacy_ingress() -> None:
    for path in (INFRA / "main.tf", PROVISION / "assets/terraform/main.tf"):
        source = path.read_text()
        assert "oidc_issuer_enabled" in source and "workload_identity_enabled" in source
        assert "web_app_routing" not in source
        assert "nginx" not in source.lower()
        assert '"kubelet_exact_acr_pull"' in source
        assert 'role_definition_name = "AcrPull"' in source
        assert "azurerm_container_registry.app.id" in source


def test_every_runtime_actor_has_one_exact_federated_subject_and_contract() -> None:
    for source in (WORKLOAD_IDENTITIES, ASSET_IDENTITIES):
        assert 'for_each  = local.workload_identity_subjects' in source
        assert 'audience  = ["api://AzureADTokenExchange"]' in source
        for workload in WORKLOADS:
            assert re.search(rf"\b{re.escape(workload)}\s*=", source)
            assert f"system:serviceaccount:" in source
        assert "local.workload_identity_contract[name]" in source
        for denial in ("direct-queue-read", "blob-content-read-list-delete", "private-key-export", "unrelated-network"):
            assert denial in source


def test_ui_validator_publisher_deployer_and_kubelet_boundaries_are_explicit() -> None:
    source = DELIVERY_IDENTITIES + (INFRA / "main.tf").read_text() + WORKLOAD_IDENTITIES
    assert re.search(r'ui\s*= \{ identity = "none"', source)
    assert re.search(r'validator\s*= \{ identity = "none"', source)
    assert 'resource "azurerm_user_assigned_identity" "jenkins_publisher"' in source
    assert 'resource "azurerm_user_assigned_identity" "jenkins_deployer"' in source
    assert 'role_definition_name = "AcrPush"' in source
    assert 'role_definition_name = "Azure Kubernetes Service RBAC Writer"' in source
    assert 'role_definition_name = "Reader"' in source
    assert "terraform-state" in source and "key-vault-secret" in source
    assert "redis-data" in source and "postgresql-data" in source
    assert "application-pod-assumption" in source and "federation" in source
    assert "system-assigned" not in source


def test_evidence_grants_are_prefix_conditioned_and_exclude_mutation_surfaces() -> None:
    source = (INFRA / "delivery-evidence-storage.tf").read_text()
    assert source.count('condition_version  = "2.0"') == 2
    for stage in ("validation", "build", "scan", "publish", "pre-promotion", "promotion", "migration", "core", "bff", "ui", "verify", "rollback", "final"):
        assert f'"{stage}"' in source
    assert "deliveries/${var.environment}/*/${stage}/*" in source
    assert "blobs/add/action" in source and "blobs/write" in source and "blobs/read" in source
    assert "blobs/delete" in source and "blobs/tags/write" in source
    assert "listKeys/action" in source
    assert "legalHolds/*" in source and "permanentDelete/action" in source
    assert 'role_definition_name = "Storage Blob Data Reader"' in source
    assert "delivery_operators_group_object_id" in source
    assert "security_reviewers_group_object_id" in source
    assert 'principal_type       = "Group"' in source


def test_provision_skill_and_assets_describe_complete_three_service_agc_topology() -> None:
    skill = (PROVISION / "SKILL.md").read_text()
    profile = (PROVISION / "references/project-profile.md").read_text()
    bootstrap = (PROVISION / "scripts/bootstrap.sh").read_text()
    url = (PROVISION / "scripts/get-application-url.sh").read_text()
    combined = skill + profile
    for term in ("BFF", "core", "lifecycle", "ALB Controller", "gateway certificate/DNS", "PostgreSQL", "Key Vault"):
        assert term in combined
    assert "legacy Ingress" in combined and "identityless" in combined
    assert "jenkins-agent-identities.tf" in bootstrap and "delivery-evidence-storage.tf" in bootstrap
    assert "gateway/$gateway" in url and 'echo "https://$address/"' in url
    assert "nginx" not in url.lower() and "service/$service" not in url


def test_teardown_requires_identity_state_parity_and_never_uses_group_delete() -> None:
    script = (TEARDOWN / "scripts/teardown.sh").read_text()
    skill = (TEARDOWN / "SKILL.md").read_text()
    policy = (TEARDOWN / "references/teardown-policy.md").read_text()
    for workload in WORKLOADS:
        assert workload in script or "required_workloads" in script
    for address in (
        "jenkins_publisher", "jenkins_deployer", "publisher_exact_acr_push",
        "deployer_exact_aks_writer", "deployer_target_rg_reader", "kubelet_exact_acr_pull",
    ):
        assert address in script
    assert "recover/import state before destroy" in script
    assert '[[ -z "$remaining" ]]' in script
    assert "az group delete" not in script
    assert "nine workload identities" in skill + policy
    assert "identityless" in skill


def test_no_skill_asset_or_output_can_emit_credentials_or_terraform_state() -> None:
    text = "\n".join(path.read_text() for path in PROVISION.rglob("*") if path.is_file())
    assert "admin_enabled       = false" in text
    assert "kubeconfig" not in (PROVISION / "assets/terraform/outputs.tf").read_text().lower()
    outputs = (INFRA / "outputs.tf").read_text()
    assert "client_secret" not in outputs and "terraform.tfstate" not in outputs


def test_skill_assets_preserve_exact_alb_gateway_kubelet_and_ui_denial_contracts() -> None:
    root_contract = WORKLOAD_IDENTITIES + DELIVERY_IDENTITIES
    asset_contract = ASSET_IDENTITIES
    for source in (root_contract, asset_contract):
        for required in (
            "exact-agc-resource-group-configuration", "exact-subnet-join",
            "named-certificate-version-read", "named-dns-record-write",
            "private-key-export", "unrelated-certificate", "zone-destroy",
            "acr-push-delete-import-admin", "role-assignment", "federation",
            "application-pod-assumption", 'ui        = { identity = "none"',
        ):
            assert required in source
    main_asset = (PROVISION / "assets/terraform/main.tf").read_text()
    assert 'role_definition_name = "AcrPull"' in main_asset
    assert "azurerm_container_registry.app.id" in main_asset
    teardown = (TEARDOWN / "scripts/teardown.sh").read_text()
    for actor in WORKLOADS | {"jenkins_publisher", "jenkins_deployer", "kubelet_exact_acr_pull"}:
        assert actor in teardown or "required_workloads" in teardown
