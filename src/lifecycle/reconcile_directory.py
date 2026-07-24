"""Checkpointed four-hour Microsoft Entra known-user reconciliation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select

from lifecycle.employee_lifecycle import mark_departed
from storage.database import DatabaseManager
from storage.identity_models import DirectoryReconciliationRunRecord, EmployeeIdentityRecord


class DirectoryLookup(Protocol):
    def status(self, tenant_id: str, object_id: str) -> str: ...


class DirectoryLookupUnavailable(RuntimeError):
    def __init__(self, code: str = "DIRECTORY_LOOKUP_UNAVAILABLE") -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    run_id: str
    status: str
    checkpoint: str | None
    checked_count: int
    departed_count: int
    error_count: int


class DirectoryReconciler:
    def __init__(
        self,
        database: DatabaseManager,
        directory: DirectoryLookup,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        id_factory: Callable[[], str] = lambda: str(uuid4()),
        before_checkpoint: Callable[[EmployeeIdentityRecord], None] | None = None,
    ) -> None:
        self.database = database
        self.directory = directory
        self.now = now
        self.id_factory = id_factory
        self.before_checkpoint = before_checkpoint

    def run(self, run_id: str | None = None) -> ReconciliationResult:
        run_id = run_id or self.id_factory()
        with self.database.session() as session:
            run = session.get(DirectoryReconciliationRunRecord, run_id)
            if run is None:
                run = DirectoryReconciliationRunRecord(id=run_id, started_at=self.now(), status="running")
                session.add(run)
            elif run.status == "completed":
                return self._result(run)
            else:
                run.status = "running"
                run.last_error_code = None

        while True:
            with self.database.session() as session:
                run = session.get(DirectoryReconciliationRunRecord, run_id)
                statement = select(EmployeeIdentityRecord).where(EmployeeIdentityRecord.lifecycle_status == "active")
                if run is not None and run.checkpoint:
                    statement = statement.where(EmployeeIdentityRecord.id > run.checkpoint)
                employee = session.execute(statement.order_by(EmployeeIdentityRecord.id).limit(1)).scalar_one_or_none()
                if employee is None:
                    assert run is not None
                    run.status = "completed"
                    run.completed_at = self.now()
                    return self._result(run)

                checked_at = self.now()
                try:
                    state = self.directory.status(employee.tenant_id, employee.object_id)
                except DirectoryLookupUnavailable as error:
                    assert run is not None
                    run.status = "retryable_failed"
                    run.error_count += 1
                    run.last_error_code = error.code
                    return self._result(run)

                if state not in {"active", "disabled", "deleted"}:
                    assert run is not None
                    run.status = "retryable_failed"
                    run.error_count += 1
                    run.last_error_code = "DIRECTORY_STATUS_INDETERMINATE"
                    return self._result(run)

                assert run is not None
                if state in {"disabled", "deleted"}:
                    mark_departed(
                        session,
                        employee=employee,
                        directory_state=state,
                        reconciliation_run_id=run_id,
                        departed_at=checked_at,
                        id_factory=self.id_factory,
                    )
                    run.departed_count += 1
                else:
                    employee.directory_state = "active"
                    employee.lifecycle_checked_at = checked_at
                    employee.updated_at = checked_at
                run.checked_count += 1
                if self.before_checkpoint is not None:
                    self.before_checkpoint(employee)
                run.checkpoint = employee.id

    @staticmethod
    def _result(run: DirectoryReconciliationRunRecord) -> ReconciliationResult:
        return ReconciliationResult(
            run_id=run.id,
            status=run.status,
            checkpoint=run.checkpoint,
            checked_count=run.checked_count,
            departed_count=run.departed_count,
            error_count=run.error_count,
        )


def main() -> None:
    raise SystemExit("Runtime wiring is supplied by the protected lifecycle CronJob configuration.")


if __name__ == "__main__":
    main()
