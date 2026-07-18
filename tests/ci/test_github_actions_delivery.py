from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_validation_workflow_runs_on_all_refs_without_azure_credentials() -> None:
    source = (WORKFLOWS / "ci.yml").read_text()
    assert "pull_request:" in source
    assert "workflow_dispatch:" in source
    assert "actions/checkout@v4" in source
    assert "scripts/ci/validate-non-azure.sh" in source
    assert "id-token: write" not in source
    assert "azure/login" not in source


def test_delivery_workflow_uses_oidc_and_protected_environments() -> None:
    source = (WORKFLOWS / "delivery.yml").read_text()
    assert "actions: read" in source
    assert "id-token: write" in source
    assert "azure/login@v2" in source
    assert "AZURE_PUBLISHER_CLIENT_ID" in source
    assert "AZURE_DEPLOYER_CLIENT_ID" in source
    assert "environment: nonprod-publisher" in source
    assert "environment: nonprod" in source
    assert "environment: nonprod-recovery" in source
    assert "scripts/ci/build-publish.sh publish" in source
    assert "scripts/ci/promote.sh" in source
    assert "scripts/ci/rollback.sh recover" in source
    assert "actions/download-artifact@v4" in source


def test_github_oidc_federation_is_environment_and_repository_scoped() -> None:
    source = (ROOT / "infra/azure/jenkins-agent-identities.tf").read_text()
    assert "azurerm_federated_identity_credential" in source
    assert "https://token.actions.githubusercontent.com" in source
    assert "var.github_repository" in source
    assert "var.github_actions_environment" in source
    assert "environment:${var.github_actions_environment}-publisher" in source
    assert "environment:${var.github_actions_environment}" in source


def test_actions_delivery_docs_replace_jenkins_as_authority() -> None:
    docs = (ROOT / "docs/github-actions-azure.md").read_text()
    assert "GitHub Actions is the CI/CD orchestrator" in docs
    assert ".github/workflows/delivery.yml" in docs
    assert "AZURE_PUBLISHER_CLIENT_ID" in docs
    assert "AZURE_DEPLOYER_CLIENT_ID" in docs
