"""Optimistic, policy-pinned lab-reference lifecycle repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update

from storage.database import DatabaseManager
from storage.lab_models import HandsOnLabReferenceRecord, LabLinkReportRecord, LabProviderApprovalRecord, LabValidationAttemptRecord


class LabReferenceConflict(RuntimeError):
    pass


class LabReferenceUnavailable(RuntimeError):
    pass


@dataclass(slots=True)
class LabRepository:
    database: DatabaseManager

    def due(self, now: datetime, *, limit: int = 100) -> list[HandsOnLabReferenceRecord]:
        with self.database.session() as session:
            return list(session.execute(select(HandsOnLabReferenceRecord).where(
                HandsOnLabReferenceRecord.availability_state != "retired",
                HandsOnLabReferenceRecord.next_validation_due_at <= now,
            ).order_by(HandsOnLabReferenceRecord.next_validation_due_at, HandsOnLabReferenceRecord.id).limit(limit)).scalars())

    def active(self, reference_id: str, policy_version: str) -> HandsOnLabReferenceRecord:
        with self.database.session() as session:
            row = session.execute(select(HandsOnLabReferenceRecord).where(
                HandsOnLabReferenceRecord.id == reference_id,
                HandsOnLabReferenceRecord.provider_policy_version == policy_version,
                HandsOnLabReferenceRecord.availability_state.in_(("active", "reported")),
            )).scalar_one_or_none()
            if row is None:
                raise LabReferenceUnavailable("LAB_REFERENCE_UNAVAILABLE")
            approval = session.execute(select(LabProviderApprovalRecord.id).where(
                LabProviderApprovalRecord.policy_version == policy_version,
                LabProviderApprovalRecord.provider == row.provider,
                LabProviderApprovalRecord.retired_at.is_(None),
            )).scalar_one_or_none()
            if approval is None:
                raise LabReferenceUnavailable("LAB_PROVIDER_POLICY_INACTIVE")
            return row

    def report(self, reference_id: str, employee_id: str, reason: str, comment: str | None, *, expected_version: int, now: datetime) -> LabLinkReportRecord:
        report = LabLinkReportRecord(id=uuid4().hex, lab_reference_id=reference_id, employee_identity_id=employee_id, reason=reason, comment=comment, created_at=now)
        with self.database.session() as session:
            result = session.execute(update(HandsOnLabReferenceRecord).where(
                HandsOnLabReferenceRecord.id == reference_id,
                HandsOnLabReferenceRecord.row_version == expected_version,
                HandsOnLabReferenceRecord.availability_state.in_(("active", "reported")),
            ).values(
                availability_state="reported",
                next_validation_due_at=now + timedelta(minutes=15),
                row_version=HandsOnLabReferenceRecord.row_version + 1,
                updated_at=now,
            ))
            if result.rowcount != 1:
                raise LabReferenceConflict("LAB_REFERENCE_VERSION_CONFLICT")
            session.add(report)
        return report

    def record_validation(self, reference_id: str, *, expected_version: int, policy_version: str, result: str, attempted_at: datetime, validator_identity_id: str, status_code: int | None = None, redirect_domains: list[str] | None = None, duration_ms: int = 0, error_code: str | None = None, scheduled: bool = True) -> HandsOnLabReferenceRecord:
        with self.database.session() as session:
            row = session.get(HandsOnLabReferenceRecord, reference_id)
            if row is None or row.row_version != expected_version:
                raise LabReferenceConflict("LAB_REFERENCE_VERSION_CONFLICT")
            if row.availability_state == "retired":
                raise LabReferenceUnavailable("LAB_REFERENCE_RETIRED")
            if row.provider_policy_version != policy_version:
                raise LabReferenceUnavailable("LAB_PROVIDER_POLICY_MISMATCH")
            approval = session.execute(select(LabProviderApprovalRecord.id).where(
                LabProviderApprovalRecord.policy_version == policy_version,
                LabProviderApprovalRecord.provider == row.provider,
                LabProviderApprovalRecord.retired_at.is_(None),
            )).scalar_one_or_none()
            if result == "success" and approval is None:
                raise LabReferenceUnavailable("LAB_PROVIDER_POLICY_INACTIVE")
            prior = row.availability_state
            if result == "success":
                row.consecutive_validation_failures = 0
                row.last_verified_at = attempted_at
                row.next_validation_due_at = attempted_at + timedelta(hours=20)
                if prior != "reported":
                    row.availability_state = "active"
            else:
                row.consecutive_validation_failures += 1
                row.next_validation_due_at = attempted_at + timedelta(hours=20)
                if result == "final_failure" or (scheduled and row.consecutive_validation_failures >= 3):
                    row.availability_state = "unavailable"
            row.row_version += 1
            row.updated_at = attempted_at
            session.add(LabValidationAttemptRecord(
                id=uuid4().hex, lab_reference_id=row.id, policy_version=policy_version,
                attempted_at=attempted_at, result=result, status_code=status_code,
                redirect_domains=redirect_domains or [], redirect_count=len(redirect_domains or []),
                duration_ms=duration_ms, error_code=error_code, prior_state=prior,
                new_state=row.availability_state, validator_identity_id=validator_identity_id,
                evidence={},
            ))
            session.flush()
            return row

    def invalidate_removed_policy(self, provider: str, policy_version: str, *, now: datetime) -> int:
        with self.database.session() as session:
            result = session.execute(update(HandsOnLabReferenceRecord).where(
                HandsOnLabReferenceRecord.provider == provider,
                HandsOnLabReferenceRecord.provider_policy_version == policy_version,
                HandsOnLabReferenceRecord.availability_state != "retired",
            ).values(availability_state="unavailable", row_version=HandsOnLabReferenceRecord.row_version + 1, updated_at=now))
            return result.rowcount

    def retire(self, reference_id: str, *, reason: str, audit_reference: str, now: datetime) -> None:
        with self.database.session() as session:
            row = session.get(HandsOnLabReferenceRecord, reference_id)
            if row is None:
                raise LabReferenceUnavailable("LAB_REFERENCE_UNAVAILABLE")
            if row.availability_state == "retired":
                raise LabReferenceUnavailable("LAB_REFERENCE_RETIRED")
            row.availability_state = "retired"
            row.retirement_reason = reason
            row.retirement_audit_reference = audit_reference
            row.retired_at = now
            row.next_validation_due_at = None
            row.row_version += 1
            row.updated_at = now

    def replacement_from_retired(self, retired_id: str, new_id: str, *, policy_version: str, destination_url: str, now: datetime) -> HandsOnLabReferenceRecord:
        with self.database.session() as session:
            prior = session.get(HandsOnLabReferenceRecord, retired_id)
            if prior is None or prior.availability_state != "retired":
                raise LabReferenceUnavailable("RETIRED_LAB_VERSION_REQUIRED")
            replacement = HandsOnLabReferenceRecord(
                id=new_id, content_version=prior.content_version, provider=prior.provider,
                objective=prior.objective, prerequisites=prior.prerequisites,
                provider_policy_version=policy_version, lab_required=prior.lab_required,
                omission_reason=prior.omission_reason, omission_explanation=prior.omission_explanation,
                classifier_object_id=prior.classifier_object_id, classified_at=prior.classified_at,
                applicability_policy_version=prior.applicability_policy_version,
                estimated_minutes=prior.estimated_minutes, cost_status=prior.cost_status,
                destination_url=destination_url, availability_state="unavailable",
                consecutive_validation_failures=0, row_version=1,
                next_validation_due_at=now, created_at=now, updated_at=now,
            )
            session.add(replacement)
            return replacement
