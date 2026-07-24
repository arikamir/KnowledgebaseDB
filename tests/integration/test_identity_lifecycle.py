from __future__ import annotations

from datetime import datetime, timezone

import pytest

from storage.database import DatabaseManager
from storage.identity_models import EmployeeIdentityRecord
from storage.identity_repository import IdentityAccessDenied, IdentityRepository


def test_active_owner_access_and_foreign_or_departed_denial(tmp_path):
    database = DatabaseManager.create(f"sqlite:///{tmp_path / 'identity.sqlite3'}")
    with database.session() as session:
        session.add_all([
            EmployeeIdentityRecord(id="active", tenant_id="tenant", object_id="employee-a", display_name="A", lifecycle_status="active", directory_state="active"),
            EmployeeIdentityRecord(id="departed", tenant_id="tenant", object_id="employee-b", display_name="B", lifecycle_status="departed", directory_state="disabled", departed_at=datetime.now(timezone.utc), access_blocked_at=datetime.now(timezone.utc)),
        ])
    repository = IdentityRepository(database)
    assert repository.active_employee("tenant", "employee-a").id == "active"
    assert repository.bootstrap_employee("tenant", "employee-a") == ("active", "active")
    assert repository.bootstrap_employee("tenant", "employee-a") == ("active", "active")
    for object_id in ("employee-b", "employee-c"):
        with pytest.raises(IdentityAccessDenied):
            repository.active_employee("tenant", object_id)
