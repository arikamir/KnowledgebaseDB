from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/delivery-identity-boundaries-v1.json"
VALIDATE = ROOT / "scripts/azure/validate-delivery-identities.sh"
ACTORS = tuple(json.loads(POLICY.read_text())["actors"])


def reviewed_manifest(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    value = json.loads((ROOT / "config/platform-bootstrap.example.json").read_text())
    digest = json.loads(subprocess.check_output(
        [str(ROOT / "scripts/azure/compute-platform-configuration-digest.sh"), str(ROOT)], text=True,
    ))
    value["manifestStatus"] = "reviewed"
    value["configuration"].update(digest=digest["digest"], recordCount=digest["recordCount"])
    base = "/subscriptions/33333333-3333-4333-8333-333333333333/resourceGroups/rg-devopscareer-nonprod/providers/Microsoft.ManagedIdentity/userAssignedIdentities"
    value["subscriptionId"] = "33333333-3333-4333-8333-333333333333"
    value["resourceGroup"] = "rg-devopscareer-nonprod"
    value["identities"].update(
        publisher=f"{base}/publisher", deployer=f"{base}/deployer", kubelet=f"{base}/kubelet",
    )
    value["identities"]["workloads"] = {
        actor: f"{base}/{actor}" for actor in (
            "bff", "core", "lifecycle", "retention", "lab-revalidation", "migration",
            "evidence-hold-reconciler", "alb-controller", "gateway-certificate-dns",
        )
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(value))
    return path, value


def resolve(value: dict[str, object], source: str) -> object:
    current: object = value
    for part in source.split("."):
        current = current[part]  # type: ignore[index]
    return current


def boundary_report(manifest: dict[str, object]) -> dict[str, object]:
    policy = json.loads(POLICY.read_text())
    actors = {}
    for actor, contract in policy["actors"].items():
        source = contract["source"]
        if source == "identityless":
            identity = None
        elif source == "external-jenkins-cloud-provisioner":
            identity = "/subscriptions/33333333-3333-4333-8333-333333333333/resourceGroups/rg-devopscareer-nonprod/providers/Microsoft.ManagedIdentity/userAssignedIdentities/jenkins-cloud-provisioner"
        else:
            identity = resolve(manifest, source)
        actors[actor] = {"identityResourceId": identity, "allowed": contract["allowed"], "denied": contract["denied"]}
    return {"schemaVersion": 1, "manifestConfigurationDigest": manifest["configuration"]["digest"], "actors": actors}


def run_contract(tmp_path: Path, mutate=None) -> subprocess.CompletedProcess[str]:
    manifest_path, manifest = reviewed_manifest(tmp_path)
    report = boundary_report(manifest)
    if mutate:
        mutate(report)
    report_path = tmp_path / "boundaries.json"
    report_path.write_text(json.dumps(report))
    return subprocess.run(
        [str(VALIDATE), "--mode", "contract", "--manifest", str(manifest_path), "--report", str(report_path), "--policy", str(POLICY)],
        cwd=ROOT, text=True, capture_output=True,
    )


def test_complete_post_bootstrap_positive_and_negative_matrix_is_accepted(tmp_path: Path) -> None:
    result = run_contract(tmp_path)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["status"] == "delivery-identities-valid"
    assert output["crossRoleDenials"] is True
    assert set(ACTORS) == {
        "ui", "publisher", "deployer", "controller", "kubelet", "bff", "core",
        "lifecycle", "retention", "lab-revalidation", "migration",
        "evidence-hold-reconciler", "alb-controller", "gateway-certificate-dns",
    }


@pytest.mark.parametrize("actor", ACTORS)
def test_each_actor_rejects_wrong_or_cross_assumed_identity(actor: str, tmp_path: Path) -> None:
    def mutate(report):
        report["actors"][actor]["identityResourceId"] = (
            "/subscriptions/33333333-3333-4333-8333-333333333333/resourceGroups/wrong/providers/Microsoft.ManagedIdentity/userAssignedIdentities/cross-role"
        )
    result = run_contract(tmp_path, mutate)
    assert result.returncode != 0


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("field", ["allowed", "denied"])
def test_each_actor_rejects_missing_positive_or_negative_boundary(actor: str, field: str, tmp_path: Path) -> None:
    policy = json.loads(POLICY.read_text())
    if not policy["actors"][actor][field]:
        pytest.skip(f"{actor} intentionally has no {field} operations")
    result = run_contract(tmp_path, lambda report: report["actors"][actor][field].pop())
    assert result.returncode != 0


def test_manifest_digest_scope_and_additional_actor_drift_fail(tmp_path: Path) -> None:
    for mutate in (
        lambda report: report.update(manifestConfigurationDigest="sha256:" + "0" * 64),
        lambda report: report["actors"].update(unreviewed=report["actors"]["core"]),
    ):
        result = run_contract(tmp_path, mutate)
        assert result.returncode != 0


@pytest.mark.skipif(os.environ.get("PLATFORM_FINALIZATION_AUTHORIZED") != "T194", reason="live identity checks execute only during authorized T194")
def test_live_post_finalization_identity_report() -> None:
    manifest = os.environ["PLATFORM_BOOTSTRAP_MANIFEST"]
    report = os.environ["AZURE_IDENTITY_BOUNDARY_REPORT"]
    result = subprocess.run(
        [str(VALIDATE), "--mode", "live", "--manifest", manifest, "--report", report, "--policy", str(POLICY)],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr

