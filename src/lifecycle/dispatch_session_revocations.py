"""Durable bounded-retry dispatcher for lifecycle-triggered BFF revocation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from sqlalchemy import select

from lifecycle.bff_revocation_client import RevocationDeliveryError
from storage.database import DatabaseManager
from storage.identity_models import SessionRevocationOutboxRecord


RETRY_DELAYS = (1, 5, 15, 30, 60)


class RevocationClient(Protocol):
    def revoke(self, row: SessionRevocationOutboxRecord) -> None: ...


@dataclass(frozen=True, slots=True)
class DispatchOutcome:
    outbox_id: str
    status: str
    attempt_count: int
    escalation: str
    next_attempt_at: datetime | None


class SessionRevocationDispatcher:
    def __init__(
        self,
        database: DatabaseManager,
        client: RevocationClient,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.database = database
        self.client = client
        self.now = now

    def dispatch_due(self, limit: int = 100) -> list[DispatchOutcome]:
        current = self.now()
        with self.database.session() as session:
            ids = session.execute(
                select(SessionRevocationOutboxRecord.id).where(
                    SessionRevocationOutboxRecord.acknowledged_at.is_(None),
                    SessionRevocationOutboxRecord.next_attempt_at <= current,
                ).order_by(SessionRevocationOutboxRecord.next_attempt_at, SessionRevocationOutboxRecord.id).limit(limit)
            ).scalars().all()
        return [self._dispatch(outbox_id, current) for outbox_id in ids]

    def _dispatch(self, outbox_id: str, current: datetime) -> DispatchOutcome:
        with self.database.session() as session:
            row = session.get(SessionRevocationOutboxRecord, outbox_id)
            assert row is not None
            row.attempt_count += 1
            row.last_attempt_at = current
            row.updated_at = current
            try:
                self.client.revoke(row)
            except Exception as error:
                code = error.code if isinstance(error, RevocationDeliveryError) else "BFF_REVOCATION_UNAVAILABLE"
                row.last_error_code = code
                created = _aware(row.created_at)
                deadline = _aware(row.deadline_at)
                age = current - created
                if current >= deadline:
                    row.status = "deadline_breached"
                    escalation = "critical"
                elif age >= timedelta(hours=6):
                    row.status = "page_required"
                    escalation = "page"
                elif age >= timedelta(hours=2):
                    row.status = "warning_required"
                    escalation = "warning"
                else:
                    row.status = "retrying"
                    escalation = "none"
                delay = RETRY_DELAYS[min(row.attempt_count - 1, len(RETRY_DELAYS) - 1)]
                row.next_attempt_at = current + timedelta(minutes=delay)
                return DispatchOutcome(row.id, row.status, row.attempt_count, escalation, row.next_attempt_at)
            row.status = "acknowledged"
            row.acknowledged_at = current
            row.next_attempt_at = current
            row.last_error_code = None
            return DispatchOutcome(row.id, row.status, row.attempt_count, "none", None)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def main() -> None:
    raise SystemExit("Runtime wiring is supplied by the protected lifecycle CronJob configuration.")


if __name__ == "__main__":
    main()
