from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SEQUENCE = ROOT / "scripts/azure/dry-run-platform-sequence.sh"


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
        "denied": ["Global Administrator", "Owner", "GitHub Actions principal", "standing privilege", "unrelated app/data/resource access"],
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


def test_only_finalizer_can_emit_the_reviewed_manifest() -> None:
    sequence = SEQUENCE.read_text()
    bootstrap = (ROOT / "scripts/azure/bootstrap-ui-platform.sh").read_text()
    data = (ROOT / "scripts/azure/bootstrap-data-principals.sh").read_text()
    finalizer = (ROOT / "scripts/azure/finalize-ui-platform.sh").read_text()
    assert "platform-bootstrap-nonprod.json" not in bootstrap + data
    assert '"$finalizer" --' not in sequence
    assert "PLATFORM_FINALIZATION_AUTHORIZED" in finalizer and "T194" in finalizer
    assert "preflight-ui-platform.sh\" live" in finalizer
