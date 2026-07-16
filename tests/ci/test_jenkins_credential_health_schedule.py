from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/jenkins-cloud-credential-policy-v1.json"
VERIFY = ROOT / "scripts/jenkins/verify-cloud-credential.sh"
CHECK = ROOT / "scripts/jenkins/check-cloud-credential-health.sh"
INSTALL = ROOT / "scripts/jenkins/install-cloud-credential-health-job.groovy"
MANAGER = ROOT / "scripts/jenkins/configure-credential-manager.groovy"
DOCS = ROOT / "docs/jenkins-credential-manager.md"

NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)


def timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def policy() -> dict[str, object]:
    return json.loads(POLICY.read_text())


def metadata(days: int = 45, version: str = "v2") -> dict[str, object]:
    configured = policy()
    return {
        "schemaVersion": 1,
        "credentialId": configured["credentialId"],
        "cloud": configured["cloud"],
        "version": version,
        "clientId": "11111111-1111-4111-8111-111111111111",
        "tenantId": "22222222-2222-4222-8222-222222222222",
        "subscriptionId": "33333333-3333-4333-8333-333333333333",
        "issuedAt": timestamp(NOW - timedelta(days=45)),
        "expiresAt": timestamp(NOW + timedelta(days=days)),
        "capturedAt": timestamp(NOW),
        "resourceGroupId": "/subscriptions/33333333-3333-4333-8333-333333333333/resourceGroups/jenkins-aci",
        "identityResourceIds": [
            "/subscriptions/33333333-3333-4333-8333-333333333333/resourceGroups/jenkins-aci/providers/Microsoft.ManagedIdentity/userAssignedIdentities/jenkins-publisher",
            "/subscriptions/33333333-3333-4333-8333-333333333333/resourceGroups/jenkins-aci/providers/Microsoft.ManagedIdentity/userAssignedIdentities/jenkins-deployer",
        ],
    }


def assignments(report: dict[str, object]) -> list[dict[str, str]]:
    identities = report["identityResourceIds"]
    assert isinstance(identities, list)
    return [
        {"roleDefinitionName": "Jenkins ACI Provisioner", "scope": str(report["resourceGroupId"])},
        {"roleDefinitionName": "Managed Identity Operator", "scope": str(identities[0])},
        {"roleDefinitionName": "Managed Identity Operator", "scope": str(identities[1])},
    ]


def write_inputs(tmp_path: Path, days: int = 45, version: str = "v2") -> tuple[Path, Path]:
    report = metadata(days, version)
    report_path = tmp_path / "credential.json"
    assignments_path = tmp_path / "assignments.json"
    report_path.write_text(json.dumps(report))
    assignments_path.write_text(json.dumps(assignments(report)))
    return report_path, assignments_path


def verify(tmp_path: Path, days: int = 45, *, mutate=None) -> subprocess.CompletedProcess[str]:
    report = metadata(days)
    role_assignments = assignments(report)
    if mutate:
        mutate(report, role_assignments)
    report_path = tmp_path / "credential.json"
    assignments_path = tmp_path / "assignments.json"
    report_path.write_text(json.dumps(report))
    assignments_path.write_text(json.dumps(role_assignments))
    return subprocess.run(
        [str(VERIFY), "--metadata", str(report_path), "--assignments", str(assignments_path),
         "--policy", str(POLICY), "--now", timestamp(NOW)],
        cwd=ROOT, text=True, capture_output=True,
    )


def health(tmp_path: Path, days: int, now: datetime = NOW, version: str = "v2") -> subprocess.CompletedProcess[str]:
    report_path, assignments_path = write_inputs(tmp_path, days, version)
    return subprocess.run(
        [str(CHECK), "--metadata", str(report_path), "--assignments", str(assignments_path),
         "--policy", str(POLICY), "--state-dir", str(tmp_path / "state"),
         "--evidence-dir", str(tmp_path / "evidence"), "--now", timestamp(now)],
        cwd=ROOT, text=True, capture_output=True,
    )


def test_policy_fixes_stable_credential_thresholds_schedule_and_exact_scopes() -> None:
    configured = policy()
    assert configured["credentialId"] == "jenkins-azure-cloud"
    assert configured["cloud"] == "azure"
    assert configured["managerPrincipal"] == "jenkins-credential-manager"
    assert configured["healthJob"] == "jenkins-cloud-credential-health"
    assert configured["schedule"] == "H H * * *"
    assert configured["minimumValidDays"] == 30
    assert configured["alertThresholdDays"] == [30, 14, 7]
    assert configured["acknowledgementHours"] == 24
    assert configured["requiredAssignments"] == [
        {"roleDefinitionName": "Jenkins ACI Provisioner", "scopeSource": "resourceGroupId"},
        {"roleDefinitionName": "Managed Identity Operator", "scopeSource": "identityResourceIds"},
    ]
    assert "AcrPush" in configured["forbiddenRoleNames"]
    assert "Azure Kubernetes Service RBAC Cluster Admin" in configured["forbiddenRoleNames"]


def test_scope_and_expiry_verifier_accepts_only_exact_nonsecret_report(tmp_path: Path) -> None:
    result = verify(tmp_path)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output == {
        "status": "pass", "credentialId": "jenkins-azure-cloud",
        "version": "v2", "daysRemaining": 45,
    }
    serialized = result.stdout + result.stderr
    for prohibited in ("clientSecret", "password", "token"):
        assert prohibited not in serialized.lower()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda report, _: report.update(expiresAt="not-a-date"),
        lambda report, _: report.update(credentialId="fallback-credential"),
        lambda report, _: report.update(resourceGroupId="/subscriptions/wrong/resourceGroups/jenkins-aci"),
        lambda _, roles: roles.append({"roleDefinitionName": "AcrPush", "scope": "/subscriptions/333"}),
        lambda _, roles: roles.pop(),
        lambda report, roles: roles.__setitem__(0, roles[0] | {"scope": str(report["resourceGroupId"]) + "/nested"}),
    ],
)
def test_scope_and_expiry_verifier_fails_closed_on_metadata_or_assignment_drift(tmp_path: Path, mutate) -> None:
    result = verify(tmp_path, mutate=mutate)
    assert result.returncode != 0
    assert "11111111-1111-4111-8111-111111111111" not in result.stdout + result.stderr


def test_verifier_rejects_fewer_than_thirty_valid_days(tmp_path: Path) -> None:
    result = verify(tmp_path, days=29)
    assert result.returncode != 0
    assert "minimum-validity" in result.stderr


def test_daily_health_is_quiet_above_threshold_and_emits_redacted_evidence(tmp_path: Path) -> None:
    result = health(tmp_path, 45)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["status"] == "healthy"
    assert output["quarantined"] is False
    assert list((tmp_path / "evidence").glob("*.json"))
    assert not (tmp_path / "state/protected-promotion.quarantine").exists()


def test_thirty_day_alert_is_deduplicated_then_unacknowledged_state_quarantines(tmp_path: Path) -> None:
    first = health(tmp_path, 30)
    assert first.returncode == 0
    assert json.loads(first.stdout)["alert"] == "expiry-30-day"
    alerts = (tmp_path / "state/alerts.jsonl").read_text().splitlines()
    assert len(alerts) == 1

    second = health(tmp_path, 29, NOW + timedelta(hours=25))
    assert second.returncode != 0
    assert json.loads(second.stdout)["quarantined"] is True
    assert len((tmp_path / "state/alerts.jsonl").read_text().splitlines()) == 1
    assert (tmp_path / "state/protected-promotion.quarantine").exists()


@pytest.mark.parametrize(("days", "threshold"), [(14, "expiry-14-day"), (7, "expiry-7-day")])
def test_fourteen_and_seven_day_alerts_escalate_and_quarantine(tmp_path: Path, days: int, threshold: str) -> None:
    result = health(tmp_path, days)
    assert result.returncode != 0
    output = json.loads(result.stdout)
    assert output["alert"] == threshold
    assert output["escalation"] == "platform-operations-incident"
    assert output["quarantined"] is True


def test_acknowledgement_is_version_bound_and_does_not_clear_below_thirty_day_quarantine(tmp_path: Path) -> None:
    health(tmp_path, 30)
    ack = subprocess.run(
        [str(CHECK), "--acknowledge", "v2", "--operator", "platform-operator-1",
         "--state-dir", str(tmp_path / "state"), "--now", timestamp(NOW + timedelta(hours=1))],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert ack.returncode == 0, ack.stderr
    result = health(tmp_path, 29, NOW + timedelta(hours=25))
    assert result.returncode != 0
    assert json.loads(result.stdout)["quarantined"] is True


def test_new_healthy_version_cannot_clear_old_quarantine_without_smoke_gates(tmp_path: Path) -> None:
    health(tmp_path, 14, version="v1")
    assert (tmp_path / "state/protected-promotion.quarantine").exists()
    result = health(tmp_path, 60, version="v2")
    assert result.returncode != 0
    assert json.loads(result.stdout)["quarantined"] is True
    assert (tmp_path / "state/protected-promotion.quarantine").exists()


def test_installer_creates_a_daily_controller_local_nonconcurrent_job() -> None:
    source = INSTALL.read_text()
    for required in (
        "jenkins-cloud-credential-health", "H H * * *", "TimerTrigger",
        "setAssignedLabel(jenkins.selfLabel)", "setConcurrentBuild(false)",
        "check-cloud-credential-health.sh", "JENKINS_HOME", "credential-health",
    ):
        assert required in source
    for prohibited in ("AZURE_CLIENT_SECRET", "withCredentials", "credentialsId("):
        assert prohibited not in source


def test_manager_uses_a_credential_specific_local_csrf_protected_action() -> None:
    source = MANAGER.read_text()
    for required in (
        "jenkins-credential-manager", "jenkins-azure-cloud", "@RequirePOST",
        "getRemoteAddr", "127.0.0.1", "0:0:0:0:0:0:0:1", "getAuthentication2",
        "SystemCredentialsProvider", "updateCredentials", "AzureCredentials",
        "Secret.fromString", "CredentialManagerAction",
    ):
        assert required in source
    assert "CredentialsProvider.UPDATE" not in source
    assert "Jenkins.ADMINISTER" not in source
    assert "clientSecret" not in source.split("println")[-1]


def test_documentation_requires_localhost_manager_and_no_general_permission_or_secret_transport() -> None:
    docs = DOCS.read_text()
    for required in (
        "localhost-only", "CSRF crumb", "jenkins-azure-cloud",
        "No global `Credentials/Update`", "protected standard input",
        "30, 14, and 7 days", "protected promotion is quarantined",
        "identityless validator, publisher, and deployer",
    ):
        assert required in docs
