from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
ROTATE = ROOT / "scripts/azure/rotate-gateway-certificate.sh"
MANIFESTS = ROOT / "deploy/k8s/base/gateway-certificate-rotation"


def run(tmp_path: Path, action: str, *args: str, now: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(ROTATE), action, "--state-dir", str(tmp_path / "state"),
         "--evidence-dir", str(tmp_path / "evidence"), "--now", now, *args],
        cwd=ROOT, env=os.environ | {"ROTATION_MODE": "dry-run"}, text=True, capture_output=True,
    )


def report(tmp_path: Path, version: str, *, converged: bool = True) -> Path:
    path = tmp_path / f"probe-{version}.json"
    path.write_text(json.dumps({
        "schemaVersion": 1,
        "target": "public-gateway",
        "certificateVersion": version,
        "replicas": [
            {"id": "gateway-0", "san": True, "issuer": True, "expiry": True, "trust": True,
             "reload": True, "tls": True, "route": True, "ready": True},
            {"id": "gateway-1", "san": converged, "issuer": True, "expiry": True, "trust": True,
             "reload": converged, "tls": converged, "route": converged, "ready": converged},
        ],
    }))
    return path


def stage(tmp_path: Path) -> None:
    result = run(
        tmp_path, "stage", "--target", "public-gateway", "--active-version", "version-old",
        "--candidate-version", "version-new", "--candidate-created-at", "2026-07-15T00:00:00Z",
        "--candidate-expires-at", "2027-01-15T00:00:00Z", "--expected-san", "career.example.test",
        "--issuer", "ConfiguredPublicIssuer", now="2026-07-17T00:00:00Z",
    )
    assert result.returncode == 0, result.stderr


def activate(tmp_path: Path) -> None:
    result = run(
        tmp_path, "activate", "--target", "public-gateway", "--probe-report", str(report(tmp_path, "version-new")),
        now="2026-07-17T00:00:00Z",
    )
    assert result.returncode == 0, result.stderr


def test_normal_rotation_requires_all_replica_proofs_and_24_hour_overlap(tmp_path: Path) -> None:
    stage(tmp_path); activate(tmp_path)
    converged = run(
        tmp_path, "converge", "--target", "public-gateway", "--probe-report", str(report(tmp_path, "version-new")),
        now="2026-07-17T01:00:00Z",
    )
    assert converged.returncode == 0, converged.stderr
    too_early = run(
        tmp_path, "retire", "--target", "public-gateway", "--probe-report", str(report(tmp_path, "version-new")),
        now="2026-07-17T23:59:59Z",
    )
    assert too_early.returncode != 0
    retired = run(
        tmp_path, "retire", "--target", "public-gateway", "--probe-report", str(report(tmp_path, "version-new")),
        now="2026-07-18T00:00:00Z",
    )
    assert retired.returncode == 0, retired.stderr
    state = json.loads((tmp_path / "state/public-gateway.json").read_text())
    assert state["status"] == "retired" and state["activeVersion"] == "version-new"
    assert state["retiredVersions"] == ["version-old"]
    assert list((tmp_path / "evidence").glob("*.json"))


def test_partial_convergence_removes_readiness_then_quarantines_and_pages(tmp_path: Path) -> None:
    stage(tmp_path); activate(tmp_path)
    partial = run(
        tmp_path, "converge", "--target", "public-gateway",
        "--probe-report", str(report(tmp_path, "version-new", converged=False)), now="2026-07-17T01:00:00Z",
    )
    assert partial.returncode == 0
    state = json.loads((tmp_path / "state/public-gateway.json").read_text())
    assert state["status"] == "partial" and state["retryUntil"] == "2026-07-18T01:00:00Z"
    scheduled = run(tmp_path, "scheduled", now="2026-07-18T01:00:00Z")
    assert scheduled.returncode == 0
    state = json.loads((tmp_path / "state/public-gateway.json").read_text())
    assert state["status"] == "quarantined" and state["pageRequired"] is True
    source = ROTATE.read_text()
    assert "pods/status" not in source  # subresource is selected by the explicit kubectl flag
    assert "--subresource=status" in source and "CertificateConverged" in source
    assert '"${BASH_SOURCE[0]}" converge' in source
    assert '"${BASH_SOURCE[0]}" retire' in source


def test_verified_rollback_and_emergency_compromise_never_use_unsafe_fallback(tmp_path: Path) -> None:
    stage(tmp_path); activate(tmp_path)
    rollback = run(
        tmp_path, "rollback", "--target", "public-gateway", "--probe-report", str(report(tmp_path, "version-old")),
        now="2026-07-17T02:00:00Z",
    )
    assert rollback.returncode == 0, rollback.stderr
    state = json.loads((tmp_path / "state/public-gateway.json").read_text())
    assert state["status"] == "rolled_back_verified" and state["activeVersion"] == "version-old"

    emergency = run(
        tmp_path, "emergency", "--target", "public-gateway", "--compromised-version", "version-old",
        now="2026-07-17T03:00:00Z",
    )
    assert emergency.returncode == 0
    state = json.loads((tmp_path / "state/public-gateway.json").read_text())
    assert state["status"] == "emergency_revoked"
    assert state["safeFallbackAllowed"] is False and state["pageRequired"] is True
    assert "version-old" in state["compromisedVersions"]


def test_runner_is_bounded_digest_pinned_identity_bound_and_default_deny() -> None:
    cronjob = (MANIFESTS / "cronjob.yaml").read_text()
    service_account = (MANIFESTS / "service-account.yaml").read_text()
    rbac = (MANIFESTS / "rbac.yaml").read_text()
    network = (MANIFESTS / "network-policy.yaml").read_text()
    kustomization = (MANIFESTS / "kustomization.yaml").read_text()
    assert 'schedule: "17 */12 * * *"' in cronjob
    assert "concurrencyPolicy: Forbid" in cronjob and "activeDeadlineSeconds: 1800" in cronjob
    assert "@${GATEWAY_CERTIFICATE_ROTATION_IMAGE_DIGEST}" in cronjob
    assert "readOnlyRootFilesystem: true" in cronjob and 'allowPrivilegeEscalation: false' in cronjob
    assert "${GATEWAY_CERTIFICATE_DNS_CLIENT_ID}" in service_account
    assert "gateway-certificate-rotation" in service_account
    assert 'resources: ["pods/status"]' in rbac and 'verbs: ["get", "patch", "update"]' in rbac
    assert "policyTypes: [Ingress, Egress]" in network and "ingress: []" in network
    assert "KEY_VAULT_PRIVATE_ENDPOINT_CIDR" in network and "AZURE_MANAGEMENT_ENDPOINT_CIDR" in network
    for resource in ("service-account.yaml", "rbac.yaml", "cronjob.yaml", "network-policy.yaml"):
        assert resource in kustomization
