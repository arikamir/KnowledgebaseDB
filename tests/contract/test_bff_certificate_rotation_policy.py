import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/azure/rotate-bff-client-certificate.sh"


def run(*args):
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=True)


def report(path: Path, version: str):
    path.write_text(json.dumps({
        "schemaVersion": 1, "candidateVersion": version,
        "replicas": [
            {"id": "bff-0", "mountedVersion": version, "ready": True, "callback": True, "sessionRefresh": True, "delegatedToken": True, "healthToken": True},
            {"id": "bff-1", "mountedVersion": version, "ready": True, "callback": True, "sessionRefresh": True, "delegatedToken": True, "healthToken": True},
        ],
    }))


def test_dry_run_normal_rotation_enforces_convergence_24_hour_overlap_and_48_hour_deadline(tmp_path):
    state = tmp_path / "state.json"; evidence = tmp_path / "evidence"; probes = tmp_path / "probes.json"
    common = ("--state", str(state), "--evidence-dir", str(evidence))
    run("stage", *common, "--now", "2026-07-17T00:00:00Z", "--active-version", "old-v1", "--candidate-version", "new-v2")
    report(probes, "new-v2")
    run("converge", *common, "--now", "2026-07-17T01:00:00Z", "--probe-report", str(probes))
    run("activate", *common, "--now", "2026-07-17T01:00:00Z", "--probe-report", str(probes))
    run("retire", *common, "--now", "2026-07-18T01:00:00Z", "--probe-report", str(probes))
    final = json.loads(state.read_text())
    assert final["status"] == "retired" and final["retiredVersions"] == ["old-v1"]
    assert all(json.loads(path.read_text())["containsPrivateMaterial"] is False for path in evidence.glob("*.json"))


def test_failed_convergence_quarantines_after_24_hours_and_emergency_has_no_fallback(tmp_path):
    state = tmp_path / "state.json"; evidence = tmp_path / "evidence"; probes = tmp_path / "probes.json"
    common = ("--state", str(state), "--evidence-dir", str(evidence))
    run("stage", *common, "--now", "2026-07-17T00:00:00Z", "--active-version", "old-v1", "--candidate-version", "new-v2")
    report(probes, "new-v2")
    data = json.loads(probes.read_text()); data["replicas"][1]["ready"] = False; probes.write_text(json.dumps(data))
    failed = subprocess.run(["bash", str(SCRIPT), "converge", *common, "--now", "2026-07-18T00:00:00Z", "--probe-report", str(probes)], cwd=ROOT)
    assert failed.returncode != 0 and json.loads(state.read_text())["operatorReleaseRequired"] is True
    run("emergency", *common, "--now", "2026-07-18T00:01:00Z", "--version", "old-v1")
    final = json.loads(state.read_text())
    assert final["status"] == "emergency_revoked" and final["noFallback"] and final["clearSessionTokenCaches"]
