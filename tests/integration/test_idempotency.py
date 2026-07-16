from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import yaml
from pathlib import Path

from storage.database import DatabaseManager
from storage.idempotency_repository import IdempotencyConflict, IdempotencyRepository, canonical_request_hash

MANIFEST = yaml.safe_load((Path(__file__).resolve().parents[1] / "fixtures/readiness-scenario-manifest-v1.yaml").read_text())
OPERATIONS = MANIFEST["groups"]["sc032_idempotency"]["operations"]


@pytest.fixture()
def clock():
    value = [datetime(2026, 7, 16, tzinfo=timezone.utc)]
    return value


@pytest.fixture()
def repository(tmp_path, clock):
    database = DatabaseManager.create(f"sqlite:///{tmp_path / 'idempotency.sqlite3'}")
    return IdempotencyRepository(database, now=lambda: clock[0])


@pytest.fixture(params=OPERATIONS)
def operation(request):
    return request.param


def claim(repository, operation="createRoadmap", actor="employee-1", key="0123456789abcdef", payload=None):
    payload = payload or {"goal": "platform"}
    return repository.claim("employee", actor, operation, key, canonical_request_hash(payload))


def test_same_key_simultaneous_tabs(repository, operation):
    assert claim(repository, operation).action == "execute"
    with pytest.raises(IdempotencyConflict, match="IDEMPOTENCY_IN_PROGRESS") as error:
        claim(repository, operation)
    assert error.value.retry_after == 2


def test_same_key_delayed_retry_replays_exact_result(repository, operation):
    decision = claim(repository, operation)
    repository.succeed(decision.record_id, 201, {"id": "roadmap-1"}, "roadmap-1")
    replay = claim(repository, operation)
    assert (replay.action, replay.status, replay.body) == ("replay", 201, {"id": "roadmap-1"})


def test_changed_payload_rejected(repository, operation):
    claim(repository, operation)
    with pytest.raises(IdempotencyConflict, match="IDEMPOTENCY_KEY_REUSED"):
        claim(repository, operation, payload={"goal": "security"})


def test_different_actor_same_key_isolated(repository, operation):
    assert claim(repository, operation, actor="employee-1").action == "execute"
    assert claim(repository, operation, actor="employee-2").action == "execute"


def test_process_restart_expired_lease_recovers_once(repository, clock, operation):
    claim(repository, operation)
    clock[0] += timedelta(seconds=61)
    assert claim(repository, operation).action == "recover"
    clock[0] += timedelta(seconds=61)
    with pytest.raises(IdempotencyConflict, match="IDEMPOTENCY_IN_PROGRESS"):
        claim(repository, operation)


def test_timeout_after_commit_replays(repository, operation):
    decision = claim(repository, operation)
    repository.succeed(decision.record_id, 200, {"committed": True})
    assert claim(repository, operation).body == {"committed": True}


def test_retryable_failed_promotes_after_retry_after(repository, clock, operation):
    decision = claim(repository, operation)
    repository.fail(decision.record_id, retryable=True, status=503, body={"code": "PERSISTENCE_UNAVAILABLE"})
    with pytest.raises(IdempotencyConflict, match="IDEMPOTENCY_IN_PROGRESS"):
        claim(repository, operation)
    clock[0] += timedelta(seconds=3)
    assert claim(repository, operation).action == "execute"


def test_final_failed_replays(repository, operation):
    decision = claim(repository, operation)
    repository.fail(decision.record_id, retryable=False, status=422, body={"code": "FINAL"})
    assert claim(repository, operation).body == {"code": "FINAL"}


def test_expired_result_is_non_reusable_tombstone(repository, clock, operation):
    decision = claim(repository, operation)
    repository.succeed(decision.record_id, 201, {"id": "roadmap-1"})
    clock[0] += timedelta(days=31)
    assert repository.tombstone_expired_results() == 1
    with pytest.raises(IdempotencyConflict, match="IDEMPOTENCY_RESULT_EXPIRED"):
        claim(repository, operation)


def test_departed_employee_tombstones_purge_only_with_owner_graph(repository, operation):
    decision = claim(repository, operation, actor="departed-owner")
    repository.succeed(decision.record_id, 200, {"ok": True})
    assert repository.purge_departed_employee("departed-owner") == 1
    assert claim(repository, operation, actor="different-owner").action == "execute"
