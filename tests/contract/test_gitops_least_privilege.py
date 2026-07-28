from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_release_workflow_and_application_manifests_remain_least_privilege() -> None:
    workflow = (ROOT / ".github/workflows/delivery.yml").read_text().lower()
    assert "id-token: write" in workflow
    assert "contents: write" in workflow
    assert "aks get-credentials" not in workflow
    assert "terraform" not in workflow
    assert "promote.sh" not in workflow
    for path in (ROOT / "deploy/argocd").rglob("*.yaml"):
        text = path.read_text().lower()
        assert "clientsecret:" not in text
        assert "kubeconfig" not in text


def test_release_tooling_uses_immutable_maintainer_setup_actions() -> None:
    workflow = (ROOT / ".github/workflows/delivery.yml").read_text()
    assert "aquasecurity/setup-trivy@3fb12ec12f41e471780db15c232d5dd185dcb514" in workflow
    assert "anchore/sbom-action/download-syft@e22c389904149dbc22b58101806040fa8d37a610" in workflow
    assert "version: v0.70.0" in workflow
    assert "syft-version: v1.18.1" in workflow
    assert "curl -sSfL https://raw.githubusercontent.com/aquasecurity" not in workflow


def test_github_federation_uses_immutable_repository_ids() -> None:
    identities = (ROOT / "infra/azure/jenkins-agent-identities.tf").read_text()
    variables = (ROOT / "infra/azure/variables.tf").read_text()
    documentation = (ROOT / "docs/github-actions-azure.md").read_text()
    assert "github_repository_owner_id" in variables
    assert "github_repository_id" in variables
    assert "@${var.github_repository_owner_id}" in identities
    assert "@${var.github_repository_id}:environment:" in identities
    assert ":environment:infrastructure-plan" in identities
    assert ":environment:infrastructure-apply" in identities
    assert 'resource "azurerm_user_assigned_identity" "github_actions_plan"' in identities
    assert "parent_id           = azurerm_user_assigned_identity.github_actions_plan.id" in identities
    assert "principal_id         = azurerm_user_assigned_identity.github_actions_plan.principal_id" in identities
    assert "role_definition_name = \"Reader\"" in identities
    assert 'resource "azuread_app_role_assignment" "github_actions_plan_directory_read"' in identities
    assert 'app_role_ids["Directory.Read.All"]' in identities
    assert "Directory.ReadWrite.All" not in identities
    assert "Application.ReadWrite.All" not in identities
    assert "sub_claim_prefix" in documentation
    assert "repo:arikamir@10241590/KnowledgebaseDB@1305159236" in documentation
    assert "X-GitHub-Api-Version: 2026-03-10" in documentation


def test_argocd_application_set_has_no_platform_paths() -> None:
    text = (ROOT / "deploy/argocd/applicationset.yaml").read_text().lower()
    assert "infra/" not in text
    assert "gateway" not in text
    assert "namespace.yaml" not in text
