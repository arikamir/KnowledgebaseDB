from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
import yaml
from sqlalchemy import select

from lifecycle.bff_revocation_client import BffRevocationClient, RevocationDeliveryError
from lifecycle.dispatch_session_revocations import RETRY_DELAYS, SessionRevocationDispatcher
from lifecycle.reconcile_directory import DirectoryLookupUnavailable, DirectoryReconciler
from storage.database import DatabaseManager
from storage.identity_models import (
    DirectoryReconciliationRunRecord,
    EmployeeIdentityRecord,
    RetentionActionRecord,
    SessionRevocationOutboxRecord,
)


NOW = datetime(2026, 7, 17, 9, tzinfo=timezone.utc)


def utc(value):
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class Directory:
    def __init__(self, states): self.states = states
    def status(self, _tenant, object_id):
        value = self.states[object_id]
        if isinstance(value, Exception): raise value
        return value


class Client:
    def __init__(self, failures=0): self.failures = failures; self.calls = []
    def revoke(self, row):
        self.calls.append((row.tenant_id, row.object_id, row.reconciliation_run_id))
        if len(self.calls) <= self.failures: raise RevocationDeliveryError("BFF_REVOCATION_UNAVAILABLE")


def database(tmp_path):
    db = DatabaseManager.create(f"sqlite:///{tmp_path / 'lifecycle.sqlite3'}")
    with db.session() as session:
        session.add_all([
            EmployeeIdentityRecord(id="a", tenant_id="tenant", object_id="active", display_name="Active"),
            EmployeeIdentityRecord(id="b", tenant_id="tenant", object_id="disabled", display_name="Disabled"),
            EmployeeIdentityRecord(id="c", tenant_id="tenant", object_id="deleted", display_name="Deleted"),
        ])
    return db


def test_reconciliation_atomically_blocks_departure_schedules_retention_and_outbox_before_checkpoint(tmp_path):
    db = database(tmp_path)
    ids = iter(["retention-b", "outbox-b", "retention-c", "outbox-c"])
    result = DirectoryReconciler(db, Directory({"active": "active", "disabled": "disabled", "deleted": "deleted"}), now=lambda: NOW, id_factory=lambda: next(ids)).run("run-1")
    assert result.status == "completed" and result.checked_count == 3 and result.departed_count == 2
    with db.session() as session:
        run = session.get(DirectoryReconciliationRunRecord, "run-1")
        departed = session.get(EmployeeIdentityRecord, "b")
        actions = session.execute(select(RetentionActionRecord)).scalars().all()
        outbox = session.execute(select(SessionRevocationOutboxRecord)).scalars().all()
        assert run.checkpoint == "c"
        assert departed.lifecycle_status == "departed" and utc(departed.access_blocked_at) == NOW
        assert utc(departed.retention_due_at) == NOW + timedelta(days=90)
        assert len(actions) == 2 and all(utc(row.due_at) == NOW + timedelta(days=90) for row in actions)
        assert len(outbox) == 2 and all(utc(row.deadline_at) == NOW + timedelta(hours=12) for row in outbox)
        assert all(utc(row.next_attempt_at) <= NOW + timedelta(minutes=5) for row in outbox)
        assert all(utc(row.deadline_at) + timedelta(hours=4) <= NOW + timedelta(hours=24) for row in outbox)


def test_reconciliation_cron_runs_every_four_hours_without_overlap():
    manifest = yaml.safe_load(Path("deploy/k8s/base/lifecycle/reconciliation-cronjob.yaml").read_text())
    assert manifest["spec"]["schedule"] == "17 */4 * * *"
    assert manifest["spec"]["concurrencyPolicy"] == "Forbid"


def test_crash_before_checkpoint_rolls_back_departure_outbox_and_retention_then_restarts_once(tmp_path):
    db = database(tmp_path)
    crashed = False
    def hook(employee):
        nonlocal crashed
        if employee.id == "b" and not crashed:
            crashed = True
            raise RuntimeError("injected crash")
    reconciler = DirectoryReconciler(db, Directory({"active": "active", "disabled": "disabled", "deleted": "deleted"}), now=lambda: NOW, before_checkpoint=hook)
    with pytest.raises(RuntimeError, match="injected crash"):
        reconciler.run("run-crash")
    with db.session() as session:
        assert session.get(DirectoryReconciliationRunRecord, "run-crash").checkpoint == "a"
        assert session.get(EmployeeIdentityRecord, "b").lifecycle_status == "active"
        assert session.execute(select(RetentionActionRecord)).scalars().all() == []
        assert session.execute(select(SessionRevocationOutboxRecord)).scalars().all() == []
    assert reconciler.run("run-crash").status == "completed"


@pytest.mark.parametrize("status", ["disabled", "deleted"])
def test_disabled_and_deleted_are_departed_but_throttle_is_retryable_and_does_not_advance(tmp_path, status):
    db = DatabaseManager.create(f"sqlite:///{tmp_path / status}.sqlite3")
    with db.session() as session:
        session.add(EmployeeIdentityRecord(id="owner", tenant_id="tenant", object_id="owner", display_name="Owner"))
    result = DirectoryReconciler(db, Directory({"owner": status}), now=lambda: NOW).run("departure")
    assert result.departed_count == 1

    db2 = DatabaseManager.create(f"sqlite:///{tmp_path / 'throttle.sqlite3'}")
    with db2.session() as session:
        session.add(EmployeeIdentityRecord(id="owner", tenant_id="tenant", object_id="owner", display_name="Owner"))
    throttled = DirectoryReconciler(db2, Directory({"owner": DirectoryLookupUnavailable("DIRECTORY_THROTTLED")}), now=lambda: NOW).run("throttle")
    assert throttled.status == "retryable_failed" and throttled.checkpoint is None and throttled.error_count == 1
    with db2.session() as session:
        assert session.get(EmployeeIdentityRecord, "owner").lifecycle_status == "active"


def seed_outbox(db, *, created_at=NOW, deadline_at=NOW + timedelta(hours=12)):
    with db.session() as session:
        session.add(DirectoryReconciliationRunRecord(id="run", started_at=created_at, status="completed"))
        session.add(EmployeeIdentityRecord(id="owner", tenant_id="tenant", object_id="owner", display_name="Owner", lifecycle_status="departed", directory_state="disabled"))
        session.add(SessionRevocationOutboxRecord(id="outbox", reconciliation_run_id="run", employee_identity_id="owner", tenant_id="tenant", object_id="owner", departed_at=created_at, status="pending", next_attempt_at=created_at, deadline_at=deadline_at, created_at=created_at, updated_at=created_at))


def test_dispatcher_retries_at_exact_bounded_delays_then_acknowledges_idempotently(tmp_path):
    db = DatabaseManager.create(f"sqlite:///{tmp_path / 'dispatch.sqlite3'}")
    seed_outbox(db)
    clock = [NOW]
    client = Client(failures=5)
    dispatcher = SessionRevocationDispatcher(db, client, now=lambda: clock[0])
    for attempt, delay in enumerate(RETRY_DELAYS, 1):
        outcome = dispatcher.dispatch_due()[0]
        assert outcome.attempt_count == attempt
        assert outcome.next_attempt_at == clock[0] + timedelta(minutes=delay)
        clock[0] = outcome.next_attempt_at
    success = dispatcher.dispatch_due()[0]
    assert success.status == "acknowledged" and success.attempt_count == 6
    assert dispatcher.dispatch_due() == []


def test_dispatcher_crash_rolls_back_attempt_and_retries_the_same_durable_row(tmp_path):
    db = DatabaseManager.create(f"sqlite:///{tmp_path / 'dispatch-crash.sqlite3'}")
    seed_outbox(db)

    class CrashOnce:
        crashed = False
        def revoke(self, _row):
            if not self.crashed:
                self.crashed = True
                raise KeyboardInterrupt("injected process loss")

    client = CrashOnce()
    dispatcher = SessionRevocationDispatcher(db, client, now=lambda: NOW)
    with pytest.raises(KeyboardInterrupt, match="injected process loss"):
        dispatcher.dispatch_due()
    with db.session() as session:
        row = session.get(SessionRevocationOutboxRecord, "outbox")
        assert row.attempt_count == 0 and row.acknowledged_at is None
    assert dispatcher.dispatch_due()[0].status == "acknowledged"


@pytest.mark.parametrize("age,expected", [(timedelta(hours=2), "warning"), (timedelta(hours=6), "page"), (timedelta(hours=12), "critical")])
def test_dispatch_escalates_at_two_six_and_twelve_hours(age, expected, tmp_path):
    db = DatabaseManager.create(f"sqlite:///{tmp_path / expected}.sqlite3")
    seed_outbox(db, created_at=NOW - age, deadline_at=NOW if expected == "critical" else NOW + timedelta(hours=1))
    outcome = SessionRevocationDispatcher(db, Client(failures=1), now=lambda: NOW).dispatch_due()[0]
    assert outcome.escalation == expected


def test_private_bff_client_sends_only_authenticated_minimal_command_and_rejects_wrong_ack():
    captured = {}
    def handler(request):
        captured.update({"headers": request.headers, "json": request.read().decode()})
        return httpx.Response(200, json={"status": "acknowledged", "reconciliationRunId": "wrong"})
    row = SessionRevocationOutboxRecord(id="out", reconciliation_run_id="run", employee_identity_id="owner", tenant_id="tenant", object_id="object", departed_at=NOW, status="pending", next_attempt_at=NOW, deadline_at=NOW + timedelta(hours=12), created_at=NOW, updated_at=NOW)
    client = BffRevocationClient("https://bff.internal", lambda: "token", transport=httpx.MockTransport(handler))
    with pytest.raises(RevocationDeliveryError, match="BFF_REVOCATION_ACK_INVALID"):
        client.revoke(row)
    assert captured["headers"]["authorization"] == "Bearer token"
    assert "displayName" not in captured["json"] and "cookie" not in captured["json"]
