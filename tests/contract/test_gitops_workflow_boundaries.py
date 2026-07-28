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
    assert workflow["permissions"] == {"contents": "read"}
    assert "environment" not in workflow["jobs"]["validate"]
    assert workflow["jobs"]["validate"]["permissions"] == {"contents": "read"}
    assert set(workflow["jobs"]) == {"validate"}
    validate_steps = {step.get("name"): step for step in workflow["jobs"]["validate"]["steps"] if "name" in step}
    assert "terraform init -backend=false" in validate_steps["Validate Terraform without credentials"]["run"]
    assert "validation-completed" in text
    assert "terraform" in text
    for forbidden in (
        "id-token: write",
        "azure/login",
        "terraform plan",
        "terraform apply",
        "build-publish",
        "promote.sh",
        "docker build",
        "argocd app sync",
    ):
        assert forbidden not in text


def test_scope_fixture_is_auditable() -> None:
    evidence = json.loads((ROOT / "tests/contract/fixtures/gitops/workflow-scope.json").read_text())
    assert set(evidence) == {"workflow", "actor", "inputs", "changedResourceSet", "result", "evidenceLinks"}
    assert evidence["changedResourceSet"] == ["deploy/argocd/environments/nonprod/release.json"]


def test_change_plan_supports_explicit_dry_run_output() -> None:
    script = (ROOT / "scripts/ci/detect-changes.sh").read_text()
    assert "--dry-run" in script
    assert "dryRun" in script
