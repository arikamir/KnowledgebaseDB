"""Validated-principal identity and machine allowlist lookup."""

from __future__ import annotations

from sqlalchemy import select

from storage.database import DatabaseManager
from storage.identity_models import EmployeeIdentityRecord, MachinePrincipalRecord


class IdentityAccessDenied(RuntimeError):
    pass


class IdentityRepository:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def active_employee(self, tenant_id: str, object_id: str) -> EmployeeIdentityRecord:
        with self.database.session() as session:
            record = session.execute(select(EmployeeIdentityRecord).where(EmployeeIdentityRecord.tenant_id == tenant_id, EmployeeIdentityRecord.object_id == object_id)).scalar_one_or_none()
            if record is None or record.lifecycle_status != "active" or record.directory_state != "active":
                raise IdentityAccessDenied("EMPLOYEE_ACCESS_DENIED")
            session.expunge(record)
            return record

    def active_machine(self, tenant_id: str, client_id: str) -> MachinePrincipalRecord:
        with self.database.session() as session:
            record = session.execute(select(MachinePrincipalRecord).where(MachinePrincipalRecord.tenant_id == tenant_id, MachinePrincipalRecord.client_id == client_id)).scalar_one_or_none()
            if record is None or record.status != "active":
                raise IdentityAccessDenied("MACHINE_TOKEN_INVALID")
            session.expunge(record)
            return record

    def bootstrap_employee(self, tenant_id: str, object_id: str) -> tuple[str, str | None]:
        """Semantically idempotent lifecycle gate; never duplicates an identity."""
        with self.database.session() as session:
            record = session.execute(select(EmployeeIdentityRecord).where(EmployeeIdentityRecord.tenant_id == tenant_id, EmployeeIdentityRecord.object_id == object_id)).scalar_one_or_none()
            if record is None:
                return "unknown", None
            if record.lifecycle_status != "active" or record.directory_state != "active":
                return "departed", None
            return "active", record.id
