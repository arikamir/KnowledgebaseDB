from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from storage.database import DatabaseManager
from storage.lab_models import HandsOnLabReferenceRecord, LabLinkReportRecord, LabProviderApprovalRecord, LabValidationAttemptRecord
from storage.lab_repository import LabReferenceConflict, LabReferenceUnavailable, LabRepository


NOW = datetime(2026, 7, 17, 10, tzinfo=timezone.utc)


def database(tmp_path):
    db = DatabaseManager.create(f"sqlite:///{tmp_path / 'labs.sqlite3'}")
    with db.session() as session:
        session.add(LabProviderApprovalRecord(
            id="approval", policy_version="policy-v1", provider="provider",
            approved_domains=["labs.example.com"], learning_owner_approver="owner",
            security_approver="security", learning_owner_group_id="owners-group",
            security_reviewer_group_id="security-group",
            learning_membership_evidence={"audit": "owner-evidence"},
            security_membership_evidence={"audit": "security-evidence"},
            reason="Approved provider for hands-on training.", audit_reference="audit-provider",
            effective_at=NOW,
        ))
        session.add(HandsOnLabReferenceRecord(
            id="lab-v1", content_version="content-v1", provider="provider",
            objective="Deploy a service", prerequisites=[], provider_policy_version="policy-v1",
            lab_required=True, classifier_object_id="classifier", classified_at=NOW,
            applicability_policy_version="applicability-v1", estimated_minutes=25,
            cost_status="free", destination_url="https://labs.example.com/start",
            availability_state="active", consecutive_validation_failures=0,
            last_verified_at=NOW, next_validation_due_at=NOW + timedelta(hours=20),
            row_version=1, created_at=NOW, updated_at=NOW,
        ))
    return db


def test_policy_scoped_lookup_reporting_is_append_only_and_success_preserves_reported_state(tmp_path):
    db = database(tmp_path); repository = LabRepository(db)
    assert repository.active("lab-v1", "policy-v1").cost_status == "free"
    with pytest.raises(LabReferenceUnavailable): repository.active("lab-v1", "wrong-policy")
    repository.report("lab-v1", "employee", "unavailable", None, expected_version=1, now=NOW)
    with pytest.raises(LabReferenceConflict): repository.report("lab-v1", "employee", "other", None, expected_version=1, now=NOW)
    validated = repository.record_validation("lab-v1", expected_version=2, policy_version="policy-v1", result="success", attempted_at=NOW + timedelta(minutes=1), validator_identity_id="validator")
    assert validated.availability_state == "reported" and validated.consecutive_validation_failures == 0
    with db.session() as session:
        assert len(session.execute(select(LabLinkReportRecord)).scalars().all()) == 1
        assert len(session.execute(select(LabValidationAttemptRecord)).scalars().all()) == 1


def test_three_scheduled_failures_make_unavailable_and_complete_success_recovers(tmp_path):
    db = database(tmp_path); repository = LabRepository(db)
    version = 1
    for attempt in range(3):
        row = repository.record_validation("lab-v1", expected_version=version, policy_version="policy-v1", result="retryable_failure", attempted_at=NOW + timedelta(hours=attempt), validator_identity_id="validator")
        version = row.row_version
    assert row.availability_state == "unavailable" and row.consecutive_validation_failures == 3
    recovered = repository.record_validation("lab-v1", expected_version=version, policy_version="policy-v1", result="success", attempted_at=NOW + timedelta(hours=4), validator_identity_id="validator")
    assert recovered.availability_state == "active" and recovered.consecutive_validation_failures == 0


def test_policy_removal_retirement_and_reversal_require_a_new_unvalidated_version(tmp_path):
    db = database(tmp_path); repository = LabRepository(db)
    assert repository.invalidate_removed_policy("provider", "policy-v1", now=NOW) == 1
    with pytest.raises(LabReferenceUnavailable): repository.active("lab-v1", "policy-v1")
    repository.retire("lab-v1", reason="Provider retired", audit_reference="audit-retire", now=NOW)
    with pytest.raises(LabReferenceUnavailable):
        repository.record_validation("lab-v1", expected_version=3, policy_version="policy-v1", result="success", attempted_at=NOW, validator_identity_id="validator")
    replacement = repository.replacement_from_retired("lab-v1", "lab-v2", policy_version="policy-v1", destination_url="https://labs.example.com/v2", now=NOW)
    assert replacement.id == "lab-v2" and replacement.availability_state == "unavailable" and replacement.row_version == 1
