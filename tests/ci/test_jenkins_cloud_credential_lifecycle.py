from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROTATE = ROOT / "scripts/jenkins/rotate-cloud-credential.sh"
HEALTH = ROOT / "scripts/jenkins/check-cloud-credential-health.sh"
VERIFY = ROOT / "scripts/jenkins/verify-cloud-credential.sh"
MANAGER = ROOT / "scripts/jenkins/configure-credential-manager.groovy"


def test_rotation_uses_only_stable_cloud_and_local_manager() -> None:
    source = ROTATE.read_text()
    for required in (
        "jenkins-azure-cloud", 'CLOUD="azure"', "127.0.0.1", "credential-manager/update",
        "--netrc-file", "Jenkins-Crumb", "@RequirePOST",
    ):
        assert required in source or required in MANAGER.read_text()
    for forbidden in ("fallback-credential", "CredentialsProvider.UPDATE", "Jenkins.ADMINISTER"):
        assert forbidden not in source + MANAGER.read_text()


def test_replacement_secret_has_no_argument_environment_or_file_surface() -> None:
    source = ROTATE.read_text()
    assert "read -r NEW_SECRET" in source
    assert "read -r OLD_SECRET <&" in source
    assert "clientSecret:input" in source
    assert "--arg clientSecret" not in source
    assert "AZURE_CLIENT_SECRET" not in source
    assert "mktemp" not in source
    assert "trap cleanup EXIT" in source
    assert "unset NEW_SECRET OLD_SECRET" in source


def test_normal_matrix_keeps_old_valid_until_all_three_checks_pass() -> None:
    source = ROTATE.read_text()
    validator = source.index('smoke "azure-aci-validator"')
    publisher = source.index('smoke "azure-aci-publisher"')
    deployer = source.index('smoke "azure-aci-deployer"')
    revoke = source.index('revoke "$OLD_VERSION"')
    assert validator < publisher < deployer < revoke
    assert "7200" in source
    assert "retryAfter" in source


def test_partial_failure_quarantines_then_retry_pages_and_restores() -> None:
    source = ROTATE.read_text()
    for required in (
        "protected-promotion.quarantine", "partial_failure", "retry_pending",
        "platform-operations-incident", "restore_old", "retry_failed_restored",
    ):
        assert required in source


def test_emergency_revokes_first_disables_ordinary_and_has_no_fallback() -> None:
    source = ROTATE.read_text()
    emergency = source.split('if [[ "$MODE" == "emergency" ]]', 1)[1].split("fi\n\nmanager_update", 1)[0]
    assert emergency.index('revoke "$OLD_VERSION"') < emergency.index("manager_update")
    assert ': > "$DISABLED"' in emergency
    assert "emergency_smoke_failed" in emergency
    assert "restore_old" not in emergency


def test_success_requires_retired_credential_denial_and_emits_version_only_evidence() -> None:
    source = ROTATE.read_text()
    assert "RETIRED_DENIAL_COMMAND" in source
    assert "retiredDenied:$retired" in source and "write_evidence emergency_rotated true" in source
    assert "clientSecret" not in source.split("write_evidence()", 1)[1].split("}", 1)[0]
    assert "credentialId" in source and "oldVersion" in source and "newVersion" in source


def test_existing_health_controls_cover_thresholds_schedule_and_under_thirty_denial() -> None:
    health = HEALTH.read_text()
    verify = VERIFY.read_text()
    assert 'threshold="30"' in health and 'threshold="14"' in health and 'threshold="7"' in health
    assert "minimumValidDays" in verify and "minimum-validity" in verify
    assert "protected-promotion.quarantine" in health


def test_update_failure_cannot_revoke_old_or_clear_quarantine() -> None:
    source = ROTATE.read_text()
    update = 'manager_update "$NEW_SECRET" "$NEW_VERSION" || fail_closed manager_update_failed'
    assert update in source
    assert source.index(update) < source.rindex('revoke "$OLD_VERSION"')
    assert "rm -f \"$QUARANTINE\"" in source
