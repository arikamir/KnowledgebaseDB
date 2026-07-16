from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/jenkins-validator-policy-v1.json"
CONFIGURE = ROOT / "scripts/jenkins/configure-validator-agent.groovy"
VERIFY = ROOT / "scripts/jenkins/verify-validator-agent.sh"
SUITE = ROOT / "scripts/ci/validate-non-azure.sh"
DOCS = ROOT / "docs/jenkins-azure-cloud.md"


def valid_template() -> dict[str, object]:
    return {
        "cloud": "azure",
        "name": "azure-aci-validator",
        "label": "azure-aci-validator",
        "image": "registry.example.invalid/validator@sha256:" + "a" * 64,
        "environment": {},
        "ports": [],
        "volumes": [],
        "systemAssignedIdentity": False,
        "userAssignedIdentities": [],
    }


def verify(tmp_path: Path, template: dict[str, object]) -> subprocess.CompletedProcess[str]:
    template_path = tmp_path / "template.json"
    template_path.write_text(json.dumps(template))
    return subprocess.run(
        [str(VERIFY), "--template-json", str(template_path), "--policy", str(POLICY)],
        cwd=ROOT, text=True, capture_output=True,
    )


def test_policy_confines_every_ref_to_the_identityless_validator() -> None:
    policy = json.loads(POLICY.read_text())
    assert policy["cloud"] == "azure"
    assert policy["template"] == policy["label"] == "azure-aci-validator"
    assert policy["allRefs"] is True
    assert policy["unprotectedRefDisposition"] == "stop_after_non_azure_validation"
    assert policy["controllerOrLocalFallback"] is False
    assert policy["suiteScript"] == "scripts/ci/validate-non-azure.sh"
    assert policy["managedIdentity"] == {"systemAssigned": False, "userAssigned": []}


def test_policy_allows_only_non_azure_validation_stages() -> None:
    policy = json.loads(POLICY.read_text())
    assert set(policy["allowedStages"]) == {
        "checkout", "change-plan", "contract-drift", "lint", "typecheck",
        "unit-test", "contract-test", "non-azure-integration-test",
    }
    assert set(policy["forbiddenStages"]) == {
        "azure-login", "acr-push", "evidence-upload", "migration", "promotion",
        "deployment", "verification", "rollback",
    }


def test_configuration_builds_one_shot_identityless_template_with_pinned_image() -> None:
    source = CONFIGURE.read_text()
    assert 'withCloudName(existing.name)' in source
    assert 'withName("azure-aci-validator")' in source
    assert 'withLabel("azure-aci-validator")' in source
    assert 'VALIDATOR_IMAGE' in source and 'sha256:' in source
    assert ".withOnceRetentionStrategy()" in source
    assert ".withEnvVars([])" in source
    assert ".withPorts([])" in source
    assert ".withVolume([])" in source
    assert "managedIdentity" not in source
    assert "userAssigned" not in source


def test_non_azure_suite_is_identical_and_contains_no_delivery_commands() -> None:
    source = SUITE.read_text()
    for command in (
        "validate-api-contracts.sh", "generate_contracts.py --check", "pytest",
        "npm --prefix bff run lint", "npm --prefix bff test",
        "npm --prefix ui run lint", "npm --prefix ui test", "playwright test",
    ):
        assert command in source
    for forbidden in ("az login", "docker push", "kubectl", "terraform apply", "tofu apply"):
        assert forbidden not in source


def test_validator_preflight_accepts_only_the_exact_identityless_shape(tmp_path: Path) -> None:
    result = verify(tmp_path, valid_template())
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "validator preflight passed"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("systemAssignedIdentity", True),
        ("userAssignedIdentities", ["/subscriptions/sub/resourceGroups/rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/validator"]),
        ("environment", {"AZURE_CLIENT_ID": "forbidden"}),
        ("environment", {"KUBECONFIG": "/tmp/config"}),
        ("ports", [22]),
        ("volumes", [{"mountPath": "/credentials"}]),
        ("image", "registry.example.invalid/validator:latest"),
        ("label", "built-in"),
    ],
)
def test_validator_preflight_rejects_identity_environment_and_fallback_surfaces(
    tmp_path: Path, field: str, value: object,
) -> None:
    template = valid_template()
    template[field] = value
    result = verify(tmp_path, template)
    assert result.returncode != 0


def test_documentation_prohibits_controller_fallback_and_unprotected_delivery() -> None:
    docs = DOCS.read_text()
    assert "agent none" in docs
    assert "azure-aci-validator" in docs
    assert "Pull requests and unprotected refs stop" in docs
    assert "No controller, built-in, or local-agent fallback" in docs
    assert "publisher/deployer" in docs
