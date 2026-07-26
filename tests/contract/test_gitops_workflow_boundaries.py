from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_application_delivery_has_no_platform_mutation_commands() -> None:
    workflow = (ROOT / ".github/workflows/delivery.yml").read_text()
    forbidden = ("terraform", "az aks get-credentials", "scripts/ci/promote.sh", "bootstrap-ui-platform", "kubectl apply")
    for value in forbidden:
        assert value not in workflow.lower(), value
    assert "pull-requests: write" in workflow
    assert "id-token: write" in workflow


def test_infrastructure_workflow_is_explicitly_platform_only() -> None:
    workflow_path = ROOT / ".github/workflows/infrastructure.yml"
    workflow = yaml.safe_load(workflow_path.read_text())
    text = workflow_path.read_text().lower()
    assert workflow["jobs"]["plan"]["environment"] == "infrastructure-plan"
    assert workflow["jobs"]["apply"]["environment"] == "infrastructure-apply"
    plan_steps = {step.get("name"): step for step in workflow["jobs"]["plan"]["steps"] if "name" in step}
    assert plan_steps["Create platform plan"]["if"] == "github.event_name != 'pull_request'"
    plan_login = plan_steps["Azure OIDC login for authenticated platform plan"]
    assert plan_login["if"] == "github.event_name != 'pull_request'"
    assert "AZURE_INFRASTRUCTURE_PLAN_CLIENT_ID" in plan_login["with"]["client-id"]
    plan_command = plan_steps["Create platform plan"]["run"]
    for variable in (
        "TF_BACKEND_RESOURCE_GROUP",
        "TF_BACKEND_STORAGE_ACCOUNT",
        "TF_BACKEND_CONTAINER",
        "TF_BACKEND_KEY",
    ):
        assert f"vars.{variable}" in plan_command
    assert "terraform plan -lock=false" in plan_command
    assert workflow["jobs"]["apply"]["if"] == "github.event_name == 'workflow_dispatch' && inputs.action == 'apply'"
    assert "terraform init -backend=false" in plan_steps["Validate Terraform only"]["run"]
    assert "validation-completed" in text
    assert "terraform" in text
    for forbidden in ("build-publish", "promote.sh", "docker build", "argocd app sync"):
        assert forbidden not in text


def test_scope_fixture_is_auditable() -> None:
    evidence = json.loads((ROOT / "tests/contract/fixtures/gitops/workflow-scope.json").read_text())
    assert set(evidence) == {"workflow", "actor", "inputs", "changedResourceSet", "result", "evidenceLinks"}
    assert evidence["changedResourceSet"] == ["deploy/argocd/environments/nonprod/release.json"]


def test_change_plan_supports_explicit_dry_run_output() -> None:
    script = (ROOT / "scripts/ci/detect-changes.sh").read_text()
    assert "--dry-run" in script
    assert "dryRun" in script
