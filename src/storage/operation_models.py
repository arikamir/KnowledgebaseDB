"""Persistent actor-scoped idempotency state."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from storage.database import Base, utcnow


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("actor_type", "actor_id", "operation", "idempotency_key", name="uq_idempotency_scope"),
        CheckConstraint("actor_type IN ('employee','application')", name="ck_idempotency_actor_type"),
        CheckConstraint("status IN ('processing','succeeded','retryable_failed','final_failed')", name="ck_idempotency_status"),
        CheckConstraint("execution_lease_expires_at > last_heartbeat_at", name="ck_idempotency_lease_after_heartbeat"),
        CheckConstraint("status NOT IN ('processing','retryable_failed') OR expires_at IS NULL", name="ck_live_idempotency_not_expiring"),
        CheckConstraint("status NOT IN ('succeeded','final_failed') OR response_status IS NOT NULL", name="ck_terminal_idempotency_has_status"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    canonical_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="processing", nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    resource_reference: Mapped[str | None] = mapped_column(String(256))
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    execution_lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tombstoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    principal_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
