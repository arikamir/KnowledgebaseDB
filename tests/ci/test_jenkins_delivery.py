from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[2]
JENKINSFILE = ROOT / "Jenkinsfile"
AUDIT_JAVA = ROOT / "jenkins-controller-audit-plugin/src/main/java/io/knowledgebasedb/jenkins/audit"
NOTIFY = ROOT / "scripts/ci/notify-delivery.sh"
LOCK = ROOT / "scripts/ci/environment-lock.sh"

CONTROLLER_CASES = {
    "SC036.accepted.success",
    "SC036.accepted.failure",
    "SC036.accepted.abort",
    "SC036.trigger.unaccepted",
    "SC036.controller.restart",
    "SC036.controller.disk_loss_restore",
    "SC036.agent.pre_allocation_failure",
    "SC036.agent.connection",
    "SC036.repository.missing_audit_call",
    "SC036.repository.shadow_attempt",
}


def source(path: str) -> str:
    return (ROOT / path).read_text()


def run(script: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(script), *args], cwd=ROOT, env=env, text=True, capture_output=True, check=False
    )


def test_sc036_sc048_manifest_freezes_exactly_the_ten_controller_cases() -> None:
    manifest = yaml.safe_load((ROOT / "tests/fixtures/readiness-scenario-manifest-v1.yaml").read_text())
    group = manifest["groups"]["sc036_sc048_controller_audit"]
    assert group["denominator"] == 10
    assert set(group["cases"]) == CONTROLLER_CASES
    assert len(group["cases"]) == len(set(group["cases"])) == 10


def test_trusted_listener_covers_acceptance_terminal_abort_restart_and_restore() -> None:
    listener = (AUDIT_JAVA / "ControllerAuditRunListener.java").read_text()
    action = (AUDIT_JAVA / "ControllerAuditAction.java").read_text()
    maintenance = (AUDIT_JAVA / "ControllerAuditMaintenance.java").read_text()
    store = (AUDIT_JAVA / "ControllerAuditStore.java").read_text()
    assert "onStarted" in listener and "run.addAction(action)" in listener and "action.start()" in listener
    assert "run.getCauses().isEmpty()" in listener  # unaccepted webhook/SCM trigger has no Run
    assert 'Result.ABORTED ? "aborted"' in listener
    assert "onCompleted" in listener and "onFinalized" in listener
    assert "if (terminalFinalized) return false" in action
    assert "restoredFromReplica" in maintenance and "aborted_recovered" in maintenance
    assert all(field in maintenance for field in ("queueAccepted", "webhookAccepted", "azureEvidenceFound"))
    assert "environmentMutated" in maintenance and "recoveryVerified" in maintenance
    assert "force(true)" in store and 'resolve(".recovery-block")' in store


def test_missing_or_shadow_repository_audit_cannot_replace_controller_authority() -> None:
    pipeline = JENKINSFILE.read_text()
    helper = source("scripts/ci/manage-controller-audit.sh")
    listener = (AUDIT_JAVA / "ControllerAuditRunListener.java").read_text()
    assert "extends RunListener" in listener and "Jenkinsfile" not in listener
    assert '^(update|export)$' in helper
    assert "/create" not in helper and "/finalize" not in helper and "/suppress" not in helper
    assert "manage-controller-audit.sh update" in pipeline
    assert "manage-controller-audit.sh export" in pipeline
    assert "CONTROLLER_AUDIT_RUN_URL" in pipeline


def test_pipeline_confines_refs_and_preserves_validator_publisher_deployer_boundaries() -> None:
    pipeline = JENKINSFILE.read_text()
    assert "agent none" in pipeline
    assert "azure-aci-validator" in pipeline
    assert "azure-aci-publisher" in pipeline
    assert "azure-aci-deployer" in pipeline
    assert "Unprotected ref completed identityless validation" in pipeline
    assert "validate-api-contracts.sh" in pipeline  # includes frozen traceability/readiness drift gate
    assert "validate-service.sh --plan" in pipeline
    assert "stash name: 'validated-change-plan'" in pipeline
    assert "unstash 'validated-change-plan'" in pipeline
    assert "stash name: 'published-release'" in pipeline
    assert "unstash 'published-release'" in pipeline
    assert "verify-aci-identity-binding.sh" in pipeline
    assert "validate-delivery-identities.sh --mode live" in pipeline
    assert "preflight-ui-platform.sh live" in pipeline


def test_manual_actions_are_protected_separated_audited_and_recovery_only() -> None:
    pipeline = JENKINSFILE.read_text()
    detector = source("scripts/ci/detect-changes.sh")
    rollback = source("scripts/ci/rollback.sh")
    assert "PROTECTED_DELIVERY" in pipeline and "SOURCE_REVISION" in pipeline
    assert '"$RECOVERY_OPERATOR" != "$PLATFORM_APPROVER"' in pipeline
    assert "manual-action-audit.json" in pipeline and "ACTION_REASON" in pipeline
    assert "Recovery-only bounded reconciliation" in pipeline
    assert "DELIVERY_ACTION == 'recovery'" in pipeline
    assert "delivery-recovery-operator" in rollback and "platform-operations" in rollback
    assert '"$OPERATOR" != "$APPROVER"' in rollback
    assert "audited-rebuild-all" in detector and "audited-recovery" in detector


def test_delivery_matrix_has_fail_fast_evidence_digest_reuse_and_bounded_compensation() -> None:
    pipeline = JENKINSFILE.read_text()
    publish = source("scripts/ci/build-publish.sh")
    evidence = source("scripts/ci/publish-evidence.sh")
    rollback = source("scripts/ci/rollback.sh")
    journal = source("scripts/ci/mutation-journal.sh")
    assert "set -euo pipefail" in pipeline
    assert pipeline.index("pre-migration") < pipeline.index("migrate-core.sh") < pipeline.index("post-migration")
    assert "published_unpromoted" in publish and "reusedThroughFreshGates" in publish
    assert "30 * 86400" in publish and "90 * 86400" in publish
    assert "delays=(1 4 16)" in evidence
    assert "lost upload response" in evidence and 'verify_exact ""' in evidence
    assert "for delay in 0 15 45" in rollback
    assert "attempt_number=$((attempt_number + 1))" in rollback and "elapsed < 1200" in rollback
    assert "failed=1; break" in rollback and "rollback_failed" in rollback
    assert "quarantine" in rollback.lower()
    assert "previousHash" in journal and "eventHash" in journal
    assert "verify_chain" in journal and '>> "$JOURNAL"' in journal


def test_notification_contract_has_exact_routes_deadlines_and_twenty_four_hour_dedup_retry(
    tmp_path: Path,
) -> None:
    policy = json.loads((ROOT / "config/jenkins-delivery-notifications-v1.json").read_text())
    assert policy == {
        "schemaVersion": 1,
        "retryWindowHours": 24,
        "events": {
            "application_pre_mutation_failure": {"routes": ["application-operations", "delivery-operators"], "acknowledgeMinutes": 240, "escalateMinutes": 480, "terminalOutcome": "failed_pre_mutation"},
            "platform_pre_mutation_failure": {"routes": ["platform-operations", "delivery-operators"], "acknowledgeMinutes": 30, "escalateMinutes": 60, "terminalOutcome": "failed_pre_mutation"},
            "evidence_failure": {"routes": ["platform-operations", "delivery-operators", "security-reviewers"], "acknowledgeMinutes": 30, "escalateMinutes": 60, "terminalOutcome": "evidence_blocked_or_rolling_back"},
            "post_mutation_failure": {"routes": ["application-operations", "platform-operations"], "acknowledgeMinutes": 15, "escalateMinutes": 30, "terminalOutcome": "rolling_back"},
            "rollback_failed": {"routes": ["application-operations", "platform-operations", "security-reviewers-when-evidence-affected"], "acknowledgeMinutes": 15, "escalateMinutes": 30, "terminalOutcome": "rollback_failed"},
            "protected_delivery_succeeded": {"routes": ["delivery-operators", "application-operations"], "acknowledgeMinutes": None, "escalateMinutes": None, "terminalOutcome": "succeeded"},
        },
    }
    sender = tmp_path / "sender"
    marker = tmp_path / "sender.failed"
    sender.write_text(
        "#!/usr/bin/env bash\n"
        "payload=$(cat)\n"
        "jq -e '.deduplicationKey==\"build-42/evidence_failure\"' <<<\"$payload\" >/dev/null\n"
        f"if [[ ! -e {marker!s} ]]; then touch {marker!s}; exit 1; fi\n"
    )
    sender.chmod(0o755)
    state = tmp_path / "state"
    env = os.environ | {"DELIVERY_NOTIFY_COMMAND": str(sender)}
    first = run(NOTIFY, "--build-id", "build-42", "--event", "evidence_failure", "--state-dir", str(state), "--now", "2026-07-17T00:00:00Z", env=env)
    second = run(NOTIFY, "--build-id", "build-42", "--event", "evidence_failure", "--state-dir", str(state), "--now", "2026-07-17T00:01:00Z", env=env)
    third = run(NOTIFY, "--build-id", "build-42", "--event", "evidence_failure", "--state-dir", str(state), "--now", "2026-07-17T23:59:00Z", env=env)
    assert first.returncode != 0
    assert second.returncode == third.returncode == 0
    record = json.loads((state / "build-42-evidence_failure.json").read_text())
    assert record["deduplicationKey"] == "build-42/evidence_failure"
    assert record["attempts"] == 2 and record["sent"] is True


def test_environment_lock_rejects_stale_concurrent_and_foreign_release(tmp_path: Path) -> None:
    state = tmp_path / "locks"
    revision = "a" * 40
    stale = run(LOCK, "acquire", "--state-dir", str(state), "--environment", "nonprod", "--attempt", "build-1", "--revision", revision, "--expected-revision", "b" * 40)
    acquired = run(LOCK, "acquire", "--state-dir", str(state), "--environment", "nonprod", "--attempt", "build-1", "--revision", revision, "--expected-revision", revision)
    concurrent = run(LOCK, "acquire", "--state-dir", str(state), "--environment", "nonprod", "--attempt", "build-2", "--revision", revision, "--expected-revision", revision)
    foreign = run(LOCK, "release", "--state-dir", str(state), "--environment", "nonprod", "--attempt", "build-2")
    released = run(LOCK, "release", "--state-dir", str(state), "--environment", "nonprod", "--attempt", "build-1")
    assert stale.returncode != 0
    assert acquired.returncode == 0
    assert concurrent.returncode != 0
    assert foreign.returncode != 0
    assert released.returncode == 0
