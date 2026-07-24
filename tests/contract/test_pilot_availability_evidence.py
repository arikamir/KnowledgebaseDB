from pathlib import Path
import json
import os
import subprocess
import yaml


ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "config/pilot-availability-profile-v1.yaml"
CLOSE = ROOT / "scripts/operations/close-pilot-availability-month.sh"
TERRAFORM = ROOT / "infra/azure/monitoring.tf"


def test_pilot_profile_fixes_window_denominator_and_maintenance_rules() -> None:
    p = yaml.safe_load(PROFILE.read_text())
    assert p["timezone"] == "Asia/Jerusalem"
    assert p["businessDays"] == ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
    assert p["window"] == {"start": "08:00", "end": "18:00"}
    assert p["observationIntervalMinutes"] == 1
    assert p["targetAvailabilityPercent"] == 99.0
    assert p["maintenance"] == {"minimumNoticeHours": 24, "monthlyExclusionCapMinutes": 240}
    assert p["missedObservationDisposition"] == "failed"
    assert p["nextPilotOpening"]["blockWhenPriorMonthCloseMissing"] is True


def test_monthly_close_is_deterministic_immutable_and_separated() -> None:
    source = CLOSE.read_text()
    for required in ("calendar-month", "scheduledMinutes", "eligibleMinutes", "successfulMinutes", "failedMinutes", "availabilityPercent", "application-operations", "platform-operations", "--if-none-match '*'", "pilot-opening.blocked", "--check-opening", "prior calendar-month close missing"):
        assert required in source
    assert "owner" in source and "coApprover" in source
    assert "mktemp" in source and "mv" in source


def test_terraform_requires_one_observation_per_eligible_minute_and_missed_run_alert() -> None:
    source = TERRAFORM.read_text()
    assert "pilot-availability-profile-v1.yaml" in source
    assert "PT1M" in source
    assert "pilot-availability-missed-observation" in source
    assert "pilot_availability_observation" in source


def test_close_counts_missing_observation_as_failure_and_honors_noticed_maintenance(tmp_path: Path) -> None:
    schedule = tmp_path / "schedule.jsonl"
    observations = tmp_path / "observations.jsonl"
    maintenance = tmp_path / "maintenance.jsonl"
    schedule.write_text("\n".join(json.dumps({"timestamp": value}) for value in (
        "2026-07-01T05:00:00Z", "2026-07-01T05:01:00Z", "2026-07-01T05:02:00Z",
    )) + "\n")
    observations.write_text(json.dumps({"timestamp": "2026-07-01T05:00:00Z", "success": True}) + "\n")
    maintenance.write_text(json.dumps({
        "start": "2026-07-01T05:02:00Z", "end": "2026-07-01T05:03:00Z",
        "announcedAt": "2026-06-29T05:02:00Z",
    }) + "\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    az = binary / "az"
    az.write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> \"$AZ_LOG\"\n")
    az.chmod(0o755)
    result = subprocess.run([
        str(CLOSE), "--month", "2026-07", "--schedule", str(schedule),
        "--observations", str(observations), "--maintenance", str(maintenance),
        "--owner", "application-operations:app-owner", "--co-approver", "platform-operations:platform-reviewer",
        "--evidence-dir", str(tmp_path / "evidence"), "--gate-dir", str(tmp_path / "gate"),
    ], cwd=ROOT, env=os.environ | {
        "PATH": f"{binary}:{os.environ['PATH']}", "AZ_LOG": str(tmp_path / "az.log"),
        "EVIDENCE_ACCOUNT": "evidenceaccount", "EVIDENCE_CONTAINER": "delivery-evidence",
    }, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    evidence = json.loads((tmp_path / "evidence/2026-07/monthly-close.json").read_text())
    assert evidence["scheduledMinutes"] == 3
    assert evidence["excludedMinutes"] == 1
    assert evidence["eligibleMinutes"] == 2
    assert evidence["successfulMinutes"] == 1
    assert evidence["failedMinutes"] == 1
    assert evidence["availabilityPercent"] == 50
    assert "--if-none-match *" in (tmp_path / "az.log").read_text()
    assert not (tmp_path / "gate/pilot-opening.blocked").exists()
