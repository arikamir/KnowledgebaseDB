from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
SEQUENCE = ROOT / "scripts/azure/dry-run-platform-sequence.sh"
VERIFY_IDENTITY = ROOT / "scripts/jenkins/verify-managed-identity.sh"
VERIFY_AGENT = ROOT / "scripts/jenkins/verify-agent.sh"


def stamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value))
    return path


def dry_run_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    now = datetime.now(timezone.utc)
    authorization = {
        "schemaVersion": 1, "activatedAt": stamp(now - timedelta(minutes=5)),
        "expiresAt": stamp(now + timedelta(hours=1)), "actorObjectId": "platform-operator",
        "consentApprover": {"objectId": "security-approver", "role": "Privileged Role Administrator"},
        "roles": [
            "Application Administrator", "Contributor:application-rg",
            "Network Contributor:named-shared-network", "Private DNS Zone Contributor:named-zones",
            "ProviderQuotaRead:allowlisted", "Role Based Access Control Administrator:application-rg",
            "Storage Blob Data Contributor:state-container",
        ],
        "denied": ["Global Administrator", "Owner", "Jenkins principal", "standing privilege", "unrelated app/data/resource access"],
    }
    attestation = {
        "schemaVersion": 1, "capturedAt": stamp(now - timedelta(minutes=5)),
        "expiresAt": stamp(now + timedelta(days=6)), "providers": {}, "quotas": {}, "capacity": {},
    }
    principals = {
        "schemaVersion": 1,
        "postgresql": {name: "11111111-1111-4111-8111-111111111111" for name in ("core-dml", "lab-validation", "lifecycle", "migrator", "retention")},
        "redis": {"bff": "22222222-2222-4222-8222-222222222222"},
    }
    return (
        write_json(tmp_path / "authorization.json", authorization),
        write_json(tmp_path / "attestation.json", attestation),
        write_json(tmp_path / "principals.json", principals),
    )


def reviewed_manifest(tmp_path: Path) -> Path:
    manifest = json.loads((ROOT / "config/platform-bootstrap.example.json").read_text())
    digest = json.loads(subprocess.check_output(
        [str(ROOT / "scripts/azure/compute-platform-configuration-digest.sh"), str(ROOT)], text=True,
    ))
    manifest["manifestStatus"] = "reviewed"
    manifest["configuration"]["digest"] = digest["digest"]
    manifest["configuration"]["recordCount"] = digest["recordCount"]
    manifest["subscriptionId"] = "33333333-3333-4333-8333-333333333333"
    manifest["resourceGroup"] = "rg-devopscareer-nonprod"
    base = "/subscriptions/33333333-3333-4333-8333-333333333333/resourceGroups/rg-devopscareer-nonprod/providers/Microsoft.ManagedIdentity/userAssignedIdentities"
    manifest["identities"]["publisher"] = f"{base}/publisher"
    manifest["identities"]["deployer"] = f"{base}/deployer"
    manifest["identities"]["kubelet"] = f"{base}/kubelet"
    manifest["identities"]["workloads"] = {
        name: f"{base}/{name}" for name in (
            "bff", "core", "lifecycle", "retention", "lab-revalidation", "migration",
            "evidence-hold-reconciler", "alb-controller", "gateway-certificate-dns",
        )
    }
    return write_json(tmp_path / "manifest.json", manifest)


def validator_template(tmp_path: Path) -> Path:
    return write_json(tmp_path / "validator.json", {
        "cloud": "azure", "name": "azure-aci-validator", "label": "azure-aci-validator",
        "image": "registry.example.invalid/validator@sha256:" + "a" * 64,
        "environment": {}, "ports": [], "volumes": [],
        "systemAssignedIdentity": False, "userAssignedIdentities": [],
    })


def test_external_sequence_dry_run_preserves_order_and_cannot_mutate_or_emit(tmp_path: Path) -> None:
    authorization, attestation, principals = dry_run_inputs(tmp_path)
    result = subprocess.run(
        [str(SEQUENCE), "--authorization", str(authorization), "--attestation", str(attestation), "--principals", str(principals)],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout.splitlines()[-1])
    assert report["status"] == "dry-run-valid"
    assert report["liveMutation"] is False and report["manifestEmitted"] is False
    assert report["order"] == [
        "terraform-apply-or-import", "data-principal-bootstrap",
        "alb-controller-install-and-attestation", "migration-guardrails-install-and-attestation",
        "identity-denial-attestation", "sole-finalization",
    ]
    assert report["liveExecutionGate"] == "T194"
    assert not (ROOT / "config/platform-bootstrap-nonprod.json").exists()


def test_jenkins_identity_verifier_consumes_canonical_preflight_for_every_actor(tmp_path: Path) -> None:
    manifest_path = reviewed_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    for actor, resource_id in {
        "publisher": manifest["identities"]["publisher"],
        "deployer": manifest["identities"]["deployer"],
        "core": manifest["identities"]["workloads"]["core"],
        "validator": "none", "ui": "none",
    }.items():
        result = subprocess.run(
            [str(VERIFY_IDENTITY), "--manifest", str(manifest_path), "--actor", actor, "--resource-id", resource_id],
            cwd=ROOT, text=True, capture_output=True,
        )
        assert result.returncode == 0, result.stderr
    source = VERIFY_IDENTITY.read_text()
    assert "preflight-ui-platform.sh" in source
    assert "compute-platform-configuration-digest.sh" not in source
    assert "platform-bootstrap.schema.json" not in source


@pytest.mark.parametrize("actor", ["publisher", "deployer", "core", "validator"])
def test_jenkins_identity_verifier_rejects_wrong_missing_or_cross_actor_binding(tmp_path: Path, actor: str) -> None:
    manifest_path = reviewed_manifest(tmp_path)
    result = subprocess.run(
        [str(VERIFY_IDENTITY), "--manifest", str(manifest_path), "--actor", actor,
         "--resource-id", "/subscriptions/999/resourceGroups/wrong/providers/Microsoft.ManagedIdentity/userAssignedIdentities/wrong"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode != 0


def test_agent_verifier_keeps_validator_identityless_and_delivery_agents_terraform_free(tmp_path: Path) -> None:
    manifest_path = reviewed_manifest(tmp_path)
    validator = subprocess.run(
        [str(VERIFY_AGENT), "--manifest", str(manifest_path), "--actor", "validator",
         "--resource-id", "none", "--template-json", str(validator_template(tmp_path))],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert validator.returncode == 0, validator.stderr
    assert json.loads(validator.stdout)["terraform"] is False
    manifest = json.loads(manifest_path.read_text())
    for actor in ("publisher", "deployer"):
        result = subprocess.run(
            [str(VERIFY_AGENT), "--manifest", str(manifest_path), "--actor", actor,
             "--resource-id", manifest["identities"][actor]], cwd=ROOT, text=True, capture_output=True,
        )
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["terraform"] is False and report["stateRead"] is False


def test_only_finalizer_can_emit_the_reviewed_manifest() -> None:
    sequence = SEQUENCE.read_text()
    bootstrap = (ROOT / "scripts/azure/bootstrap-ui-platform.sh").read_text()
    data = (ROOT / "scripts/azure/bootstrap-data-principals.sh").read_text()
    finalizer = (ROOT / "scripts/azure/finalize-ui-platform.sh").read_text()
    assert "platform-bootstrap-nonprod.json" not in bootstrap + data
    assert '"$finalizer" --' not in sequence
    assert "PLATFORM_FINALIZATION_AUTHORIZED" in finalizer and "T194" in finalizer
    assert "preflight-ui-platform.sh\" live" in finalizer
