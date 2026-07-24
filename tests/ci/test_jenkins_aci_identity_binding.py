from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tests/fixtures/readiness-scenario-manifest-v1.yaml"
VERIFY = ROOT / "scripts/jenkins/verify-aci-identity-binding.sh"
POLICY = ROOT / "config/jenkins-aci-identity-policy-v1.json"

PUBLISHER = "/subscriptions/33333333-3333-4333-8333-333333333333/resourceGroups/rg-devopscareer-nonprod/providers/Microsoft.ManagedIdentity/userAssignedIdentities/publisher"
DEPLOYER = "/subscriptions/33333333-3333-4333-8333-333333333333/resourceGroups/rg-devopscareer-nonprod/providers/Microsoft.ManagedIdentity/userAssignedIdentities/deployer"


def bootstrap() -> dict[str, object]:
    return {
        "schemaVersion": 1, "manifestStatus": "reviewed", "environment": "nonprod",
        "subscriptionId": "33333333-3333-4333-8333-333333333333",
        "resourceGroup": "rg-devopscareer-nonprod", "state": {"locked": True},
        "resources": {
            "aksId": "/subscriptions/33333333-3333-4333-8333-333333333333/resourceGroups/rg-devopscareer-nonprod/providers/Microsoft.ContainerService/managedClusters/aks",
            "acrId": "/subscriptions/33333333-3333-4333-8333-333333333333/resourceGroups/rg-devopscareer-nonprod/providers/Microsoft.ContainerRegistry/registries/acr",
        },
        "identities": {"validator": None, "ui": None, "publisher": PUBLISHER, "deployer": DEPLOYER},
        "review": {"generatedAt": "2026-07-17T00:00:00Z", "expiresAt": "2026-07-24T00:00:00Z"},
    }


def template(name: str, identities: list[str]) -> dict[str, object]:
    return {"name": name, "label": name, "systemAssignedIdentity": False, "userAssignedIdentities": identities}


def valid_inputs(reference: str = "protected") -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    templates = {
        "schemaVersion": 1, "cloud": "azure", "controllerOrLocalFallback": False,
        "templates": {
            "validator": template("azure-aci-validator", []),
            "publisher": template("azure-aci-publisher", [PUBLISHER]),
            "deployer": template("azure-aci-deployer", [DEPLOYER]),
        },
    }
    runtime = {
        "validator": {"systemAssignedIdentity": False, "userAssignedIdentities": []},
        "publisher": {"systemAssignedIdentity": False, "userAssignedIdentities": [PUBLISHER]},
        "deployer": {"systemAssignedIdentity": False, "userAssignedIdentities": [DEPLOYER]},
    }
    requested = ["validator", "publisher", "deployer"] if reference == "protected" else ["validator"]
    stages = ({
        "validator": ["contract-test"], "publisher": ["publish"], "deployer": ["deployment"]
    } if reference == "protected" else {"validator": ["contract-test"]})
    authorization = {
        "referenceType": reference, "requestedTemplates": requested, "requestedStages": stages,
        "publisherAssignments": [{"roleDefinitionName": "AcrPush", "scope": bootstrap()["resources"]["acrId"]}],
        "deployerAssignments": [
            {"roleDefinitionName": "Reader", "scope": "/subscriptions/33333333-3333-4333-8333-333333333333/resourceGroups/rg-devopscareer-nonprod"},
            {"roleDefinitionName": "Azure Kubernetes Service RBAC Writer", "scope": bootstrap()["resources"]["aksId"]},
        ],
        "requiredDenials": json.loads(POLICY.read_text())["requiredDenials"],
        "crossIdentityDenials": json.loads(POLICY.read_text())["crossIdentityDenials"],
    }
    return templates, runtime, authorization


def run_gate(tmp_path: Path, templates: dict[str, object], runtime: dict[str, object], authorization: dict[str, object]) -> subprocess.CompletedProcess[str]:
    paths = []
    for name, value in (("manifest", bootstrap()), ("templates", templates), ("runtime", runtime), ("authorization", authorization)):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(value))
        paths.append(path)
    return subprocess.run(
        [str(VERIFY), "--manifest", str(paths[0]), "--templates", str(paths[1]),
         "--runtime-identities", str(paths[2]), "--authorization", str(paths[3]),
         "--policy", str(POLICY)], cwd=ROOT, text=True, capture_output=True,
    )


def test_poc_manifest_requires_explicit_flag_and_nonformal_attestations(tmp_path: Path) -> None:
    templates, runtime, authorization = valid_inputs()
    manifest = bootstrap()
    manifest["manifestStatus"] = "poc-reviewed"
    manifest["attestations"] = {
        "jitPermissions": {"formalT194": False},
        "identityDenials": {"formalT194": False},
    }
    paths = []
    for name, value in (("manifest", manifest), ("templates", templates), ("runtime", runtime), ("authorization", authorization)):
        path = tmp_path / f"poc-{name}.json"
        path.write_text(json.dumps(value))
        paths.append(path)
    command = [
        str(VERIFY), "--manifest", str(paths[0]), "--templates", str(paths[1]),
        "--runtime-identities", str(paths[2]), "--authorization", str(paths[3]),
        "--policy", str(POLICY),
    ]
    denied = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    allowed = subprocess.run(command + ["--allow-technical-poc"], cwd=ROOT, text=True, capture_output=True)
    assert denied.returncode != 0
    assert allowed.returncode == 0, allowed.stderr


def mutate_case(case_id: str, templates: dict[str, object], runtime: dict[str, object], authorization: dict[str, object]) -> bool:
    _, actor, variant = case_id.split(".")
    if actor == "reference":
        return True
    if variant in {"required_identityless", "required_identity"}:
        return True
    shape = templates["templates"][actor]
    if variant in {"missing_declaration", "missing_identity"}:
        if actor == "validator":
            del templates["templates"][actor]
        else:
            shape["userAssignedIdentities"] = []
    elif variant == "swapped_identity":
        shape["userAssignedIdentities"] = [DEPLOYER if actor != "deployer" else PUBLISHER]
    elif variant == "additional_identity":
        shape["userAssignedIdentities"] = list(shape["userAssignedIdentities"]) + [PUBLISHER]
    elif variant == "system_assigned_identity":
        shape["systemAssignedIdentity"] = True
    else:
        raise AssertionError(case_id)
    return False


def test_sc039_manifest_is_the_exact_frozen_seventeen_case_matrix() -> None:
    group = yaml.safe_load(MANIFEST.read_text())["groups"]["sc039_agent_identity_isolation"]
    assert group["criteria"] == ["SC-039"]
    assert group["denominator"] == 17
    assert group["cases"] == [
        "SC039.validator.required_identityless", "SC039.validator.missing_declaration",
        "SC039.validator.swapped_identity", "SC039.validator.additional_identity",
        "SC039.validator.system_assigned_identity", "SC039.publisher.required_identity",
        "SC039.publisher.missing_identity", "SC039.publisher.swapped_identity",
        "SC039.publisher.additional_identity", "SC039.publisher.system_assigned_identity",
        "SC039.deployer.required_identity", "SC039.deployer.missing_identity",
        "SC039.deployer.swapped_identity", "SC039.deployer.additional_identity",
        "SC039.deployer.system_assigned_identity", "SC039.reference.pull_request",
        "SC039.reference.protected",
    ]


@pytest.mark.parametrize("case_id", yaml.safe_load(MANIFEST.read_text())["groups"]["sc039_agent_identity_isolation"]["cases"])
def test_every_sc039_identity_reference_and_stage_case(case_id: str, tmp_path: Path) -> None:
    reference = "pull_request" if case_id.endswith("pull_request") else "protected"
    templates, runtime, authorization = valid_inputs(reference)
    should_pass = mutate_case(case_id, templates, runtime, authorization)
    result = run_gate(tmp_path, deepcopy(templates), deepcopy(runtime), deepcopy(authorization))
    assert (result.returncode == 0) is should_pass, result.stderr


@pytest.mark.parametrize(
    ("actor", "stage"),
    [("validator", "publish"), ("publisher", "deployment"), ("deployer", "publish")],
)
def test_unauthorized_token_or_stage_attempts_fail(actor: str, stage: str, tmp_path: Path) -> None:
    templates, runtime, authorization = valid_inputs()
    authorization["requestedStages"][actor] = [stage]
    result = run_gate(tmp_path, templates, runtime, authorization)
    assert result.returncode != 0


@pytest.mark.parametrize("actor", ["publisher", "deployer"])
def test_delivery_identity_from_another_subscription_fails(actor: str, tmp_path: Path) -> None:
    templates, runtime, authorization = valid_inputs()
    foreign = templates["templates"][actor]["userAssignedIdentities"][0].replace(
        "33333333-3333-4333-8333-333333333333",
        "44444444-4444-4444-8444-444444444444",
    )
    templates["templates"][actor]["userAssignedIdentities"] = [foreign]
    runtime[actor]["userAssignedIdentities"] = [foreign]
    result = run_gate(tmp_path, templates, runtime, authorization)
    assert result.returncode != 0


@pytest.mark.parametrize("resource", ["aksId", "acrId"])
def test_target_resource_from_another_resource_group_fails(resource: str, tmp_path: Path) -> None:
    templates, runtime, authorization = valid_inputs()
    manifest = bootstrap()
    manifest["resources"][resource] = manifest["resources"][resource].replace(
        "resourceGroups/rg-devopscareer-nonprod",
        "resourceGroups/rg-unrelated-nonprod",
    )
    paths = []
    for name, value in (("manifest", manifest), ("templates", templates), ("runtime", runtime), ("authorization", authorization)):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(value))
        paths.append(path)
    result = subprocess.run(
        [str(VERIFY), "--manifest", str(paths[0]), "--templates", str(paths[1]),
         "--runtime-identities", str(paths[2]), "--authorization", str(paths[3]),
         "--policy", str(POLICY)], cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode != 0
