"""Identity, lifecycle, outbox, and retention ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from storage.database import Base, utcnow


class EmployeeIdentityRecord(Base):
    __tablename__ = "employee_identities"
    __table_args__ = (UniqueConstraint("tenant_id", "object_id", name="uq_employee_identity_subject"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    employee_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    directory_state: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    lifecycle_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    departed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    access_blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MachinePrincipalRecord(Base):
    __tablename__ = "machine_principals"
    __table_args__ = (UniqueConstraint("tenant_id", "client_id", name="uq_machine_principal_client"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    allowed_roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DirectoryReconciliationRunRecord(Base):
    __tablename__ = "directory_reconciliation_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checkpoint: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    checked_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    departed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(64))


class RetentionActionRecord(Base):
    __tablename__ = "retention_actions"
    __table_args__ = (
        UniqueConstraint("employee_identity_id", "operation", name="uq_retention_owner_operation"),
        CheckConstraint("status != 'completed' OR employee_identity_id IS NULL", name="ck_completed_retention_unlinked"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_identity_id: Mapped[str | None] = mapped_column(ForeignKey("employee_identities.id", ondelete="SET NULL"))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    operation: Mapped[str] = mapped_column(String(64), default="purge_owner_graph", nullable=False)
    evidence_disposition: Mapped[str] = mapped_column(String(32), default="delete", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    aggregate_counts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class SessionRevocationOutboxRecord(Base):
    __tablename__ = "session_revocation_outbox"
    __table_args__ = (
        UniqueConstraint("reconciliation_run_id", "employee_identity_id", name="uq_revocation_run_owner"),
        Index("ix_revocation_dispatch", "status", "next_attempt_at"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    reconciliation_run_id: Mapped[str] = mapped_column(ForeignKey("directory_reconciliation_runs.id"), nullable=False)
    employee_identity_id: Mapped[str] = mapped_column(ForeignKey("employee_identities.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str] = mapped_column(String(64), nullable=False)
    departed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
