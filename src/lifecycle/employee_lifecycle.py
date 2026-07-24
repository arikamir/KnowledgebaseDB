"""Atomic employee departure transition shared by directory reconciliation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from storage.identity_models import EmployeeIdentityRecord, RetentionActionRecord, SessionRevocationOutboxRecord


def mark_departed(
    session: Session,
    *,
    employee: EmployeeIdentityRecord,
    directory_state: str,
    reconciliation_run_id: str,
    departed_at: datetime,
    id_factory: Callable[[], str] = lambda: str(uuid4()),
) -> SessionRevocationOutboxRecord:
    """Block access and create both durable follow-up records in one transaction."""
    employee.lifecycle_status = "departed"
    employee.directory_state = directory_state
    employee.departed_at = employee.departed_at or departed_at
    employee.access_blocked_at = employee.access_blocked_at or departed_at
    employee.retention_due_at = employee.retention_due_at or departed_at + timedelta(days=90)
    employee.lifecycle_checked_at = departed_at
    employee.updated_at = departed_at

    retention = session.execute(
        select(RetentionActionRecord).where(
            RetentionActionRecord.employee_identity_id == employee.id,
            RetentionActionRecord.operation == "purge_owner_graph",
        )
    ).scalar_one_or_none()
    if retention is None:
        retention = RetentionActionRecord(
            id=id_factory(),
            employee_identity_id=employee.id,
            due_at=employee.retention_due_at,
            status="pending",
            operation="purge_owner_graph",
            evidence_disposition="delete",
        )
        session.add(retention)
    elif retention.status == "pending" and retention.due_at > employee.retention_due_at:
        # Lifecycle may only narrow the unclaimed schedule. Claiming, completing,
        # and reading the protected owner graph remain retention-identity duties.
        retention.due_at = employee.retention_due_at

    outbox = session.execute(
        select(SessionRevocationOutboxRecord).where(
            SessionRevocationOutboxRecord.reconciliation_run_id == reconciliation_run_id,
            SessionRevocationOutboxRecord.employee_identity_id == employee.id,
        )
    ).scalar_one_or_none()
    if outbox is None:
        outbox = SessionRevocationOutboxRecord(
            id=id_factory(),
            reconciliation_run_id=reconciliation_run_id,
            employee_identity_id=employee.id,
            tenant_id=employee.tenant_id,
            object_id=employee.object_id,
            departed_at=employee.departed_at,
            status="pending",
            next_attempt_at=departed_at,
            deadline_at=departed_at + timedelta(hours=12),
            created_at=departed_at,
            updated_at=departed_at,
        )
        session.add(outbox)
    return outbox
