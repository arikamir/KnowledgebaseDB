"""Transactional actor-scoped idempotency state machine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy import delete, select

from storage.database import DatabaseManager
from storage.operation_models import IdempotencyRecord


LEASE = timedelta(seconds=60)
HEARTBEAT = timedelta(seconds=15)
RESULT_RETENTION = timedelta(days=30)
MACHINE_RETENTION = timedelta(days=90)


def canonical_request_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class IdempotencyDecision:
    action: str
    record_id: str
    status: int | None = None
    body: dict[str, Any] | None = None
    retry_after: int | None = None


class IdempotencyConflict(RuntimeError):
    def __init__(self, code: str, retry_after: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after


class IdempotencyRepository:
    def __init__(self, database: DatabaseManager, now: Callable[[], datetime] | None = None) -> None:
        self.database = database
        self.now = now or (lambda: datetime.now(timezone.utc))

    def claim(self, actor_type: str, actor_id: str, operation: str, key: str, request_hash: str) -> IdempotencyDecision:
        now = self.now()
        with self.database.session() as session:
            query = select(IdempotencyRecord).where(
                IdempotencyRecord.actor_type == actor_type,
                IdempotencyRecord.actor_id == actor_id,
                IdempotencyRecord.operation == operation,
                IdempotencyRecord.idempotency_key == key,
            )
            record = session.execute(query).scalar_one_or_none()
            if record is None:
                record = IdempotencyRecord(
                    id=uuid4().hex, actor_type=actor_type, actor_id=actor_id, operation=operation,
                    idempotency_key=key, canonical_request_hash=request_hash, status="processing",
                    execution_lease_expires_at=now + LEASE, last_heartbeat_at=now,
                )
                session.add(record)
                session.flush()
                return IdempotencyDecision("execute", record.id)
            if record.canonical_request_hash != request_hash:
                raise IdempotencyConflict("IDEMPOTENCY_KEY_REUSED")
            if record.status == "succeeded":
                if record.response_body is None:
                    raise IdempotencyConflict("IDEMPOTENCY_RESULT_EXPIRED")
                return IdempotencyDecision("replay", record.id, record.response_status, record.response_body)
            if record.status == "final_failed":
                return IdempotencyDecision("replay", record.id, record.response_status, record.response_body)
            if record.status == "retryable_failed":
                retry_after = _aware(record.retry_after)
                if retry_after and retry_after > now:
                    seconds = max(1, int((retry_after - now).total_seconds()))
                    raise IdempotencyConflict("IDEMPOTENCY_IN_PROGRESS", seconds)
                record.status = "processing"
                record.attempt_count += 1
                record.execution_lease_expires_at = now + LEASE
                record.last_heartbeat_at = now
                return IdempotencyDecision("execute", record.id)
            lease_expires = _aware(record.execution_lease_expires_at)
            if lease_expires and lease_expires > now:
                raise IdempotencyConflict("IDEMPOTENCY_IN_PROGRESS", 2)
            if record.attempt_count >= 2:
                raise IdempotencyConflict("IDEMPOTENCY_IN_PROGRESS", 2)
            record.attempt_count += 1
            record.execution_lease_expires_at = now + LEASE
            record.last_heartbeat_at = now
            return IdempotencyDecision("recover", record.id)

    def heartbeat(self, record_id: str) -> None:
        now = self.now()
        with self.database.session() as session:
            record = session.get(IdempotencyRecord, record_id)
            if record is None or record.status != "processing":
                raise IdempotencyConflict("IDEMPOTENCY_NOT_PROCESSING")
            record.last_heartbeat_at = now
            record.execution_lease_expires_at = now + LEASE

    def reconcile_expired_lease(self, record_id: str, committed_result: tuple[int, dict[str, Any], str | None] | None) -> IdempotencyDecision:
        """Resolve resource/outbox state before the sole allowed restart."""
        if committed_result is None:
            return IdempotencyDecision("restart", record_id)
        status, body, resource_reference = committed_result
        self.succeed(record_id, status, body, resource_reference)
        return IdempotencyDecision("replay", record_id, status, body)

    def succeed(self, record_id: str, status: int, body: dict[str, Any], resource_reference: str | None = None) -> None:
        now = self.now()
        with self.database.session() as session:
            record = session.get(IdempotencyRecord, record_id)
            if record is None or record.status != "processing":
                raise IdempotencyConflict("IDEMPOTENCY_NOT_PROCESSING")
            record.status = "succeeded"
            record.response_status = status
            record.response_body = body
            record.resource_reference = resource_reference
            record.completed_at = now
            record.response_expires_at = now + RESULT_RETENTION

    def fail(self, record_id: str, *, retryable: bool, status: int, body: dict[str, Any], retry_after_seconds: int = 2) -> None:
        now = self.now()
        with self.database.session() as session:
            record = session.get(IdempotencyRecord, record_id)
            if record is None or record.status != "processing":
                raise IdempotencyConflict("IDEMPOTENCY_NOT_PROCESSING")
            record.status = "retryable_failed" if retryable else "final_failed"
            record.response_status = status
            record.response_body = body
            record.completed_at = None if retryable else now
            record.retry_after = now + timedelta(seconds=retry_after_seconds) if retryable else None
            record.response_expires_at = None if retryable else now + RESULT_RETENTION

    def tombstone_expired_results(self) -> int:
        now = self.now()
        changed = 0
        with self.database.session() as session:
            records = session.execute(select(IdempotencyRecord).where(IdempotencyRecord.status.in_(("succeeded", "final_failed")))).scalars()
            for record in records:
                expires = _aware(record.response_expires_at)
                if expires and expires <= now and record.response_body is not None:
                    record.response_body = None
                    record.tombstoned_at = now
                    changed += 1
        return changed

    def purge_departed_employee(self, actor_id: str) -> int:
        with self.database.session() as session:
            result = session.execute(delete(IdempotencyRecord).where(IdempotencyRecord.actor_type == "employee", IdempotencyRecord.actor_id == actor_id))
            return int(result.rowcount or 0)

    def purge_revoked_machines(self) -> int:
        now = self.now()
        changed = 0
        with self.database.session() as session:
            records = session.execute(select(IdempotencyRecord).where(IdempotencyRecord.actor_type == "application", IdempotencyRecord.status.in_(("succeeded", "final_failed")), IdempotencyRecord.principal_revoked_at.is_not(None))).scalars()
            for record in records:
                revoked_at = _aware(record.principal_revoked_at)
                if revoked_at and revoked_at + MACHINE_RETENTION <= now:
                    session.delete(record)
                    changed += 1
        return changed
