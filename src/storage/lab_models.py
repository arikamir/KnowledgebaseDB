"""Versioned lab-reference, provider-approval, report, and validation history."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from storage.database import Base, utcnow


class LabProviderApprovalRecord(Base):
    __tablename__ = "lab_provider_approvals"
    __table_args__ = (
        UniqueConstraint("policy_version", "provider", name="uq_lab_provider_policy"),
        CheckConstraint("learning_owner_approver != security_approver", name="ck_lab_provider_distinct_approvers"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_domains: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    learning_owner_approver: Mapped[str] = mapped_column(String(64), nullable=False)
    security_approver: Mapped[str] = mapped_column(String(64), nullable=False)
    learning_owner_group_id: Mapped[str] = mapped_column(String(64), nullable=False)
    security_reviewer_group_id: Mapped[str] = mapped_column(String(64), nullable=False)
    learning_membership_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    security_membership_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    audit_reference: Mapped[str] = mapped_column(String(256), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HandsOnLabReferenceRecord(Base):
    __tablename__ = "hands_on_lab_references"
    __table_args__ = (
        CheckConstraint("cost_status IN ('free','paid','subscription','unknown')", name="ck_lab_cost_status"),
        CheckConstraint("availability_state IN ('active','reported','unavailable','retired')", name="ck_lab_availability"),
        CheckConstraint("consecutive_validation_failures >= 0", name="ck_lab_failure_count"),
        CheckConstraint("row_version >= 1", name="ck_lab_row_version"),
        CheckConstraint("destination_url LIKE 'https://%'", name="ck_lab_https"),
        CheckConstraint("(lab_required AND omission_reason IS NULL AND omission_explanation IS NULL) OR (NOT lab_required AND omission_reason IN ('orientation','conceptual_comparison','review_only') AND length(omission_explanation) BETWEEN 20 AND 500)", name="ck_lab_applicability"),
        CheckConstraint("availability_state != 'retired' OR (retired_at IS NOT NULL AND retirement_reason IS NOT NULL)", name="ck_lab_retirement_audit"),
        Index("ix_lab_policy_state", "provider_policy_version", "availability_state"),
        Index("ix_lab_validation_due", "next_validation_due_at", "consecutive_validation_failures"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    objective: Mapped[str] = mapped_column(String(1024), nullable=False)
    prerequisites: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    provider_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    lab_required: Mapped[bool] = mapped_column(nullable=False)
    omission_reason: Mapped[str | None] = mapped_column(String(32))
    omission_explanation: Mapped[str | None] = mapped_column(String(500))
    classifier_object_id: Mapped[str] = mapped_column(String(64), nullable=False)
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    applicability_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_status: Mapped[str] = mapped_column(String(16), nullable=False)
    destination_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    availability_state: Mapped[str] = mapped_column(String(16), default="unavailable", nullable=False)
    consecutive_validation_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_validation_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retirement_reason: Mapped[str | None] = mapped_column(String(500))
    retirement_audit_reference: Mapped[str | None] = mapped_column(String(256))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class LabLinkReportRecord(Base):
    __tablename__ = "lab_link_reports"
    __table_args__ = (CheckConstraint("reason IN ('unavailable','unsuitable','cost_mismatch','other')", name="ck_lab_report_reason"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lab_reference_id: Mapped[str] = mapped_column(ForeignKey("hands_on_lab_references.id"), nullable=False, index=True)
    employee_identity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class LabValidationAttemptRecord(Base):
    __tablename__ = "lab_validation_attempts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lab_reference_id: Mapped[str] = mapped_column(ForeignKey("hands_on_lab_references.id"), nullable=False, index=True)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    redirect_domains: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    redirect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    prior_state: Mapped[str] = mapped_column(String(16), nullable=False)
    new_state: Mapped[str] = mapped_column(String(16), nullable=False)
    validator_identity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
