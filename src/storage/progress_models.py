"""Actor-owned progress check-ins and immutable review snapshots."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from storage.database import Base, utcnow


EXACT_OWNER = (
    "(actor_type = 'employee' AND employee_identity_id IS NOT NULL "
    "AND machine_principal_id IS NULL) OR "
    "(actor_type = 'application' AND machine_principal_id IS NOT NULL "
    "AND employee_identity_id IS NULL)"
)


class ProgressCheckInRecord(Base):
    __tablename__ = "owned_progress_check_ins"
    __table_args__ = (
        CheckConstraint(EXACT_OWNER, name="ck_progress_check_in_exact_owner"),
        ForeignKeyConstraint(
            ["employee_identity_id", "roadmap_id"],
            ["owned_roadmaps.employee_identity_id", "owned_roadmaps.id"],
            name="fk_progress_check_in_employee_roadmap",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["machine_principal_id", "roadmap_id"],
            ["owned_roadmaps.machine_principal_id", "owned_roadmaps.id"],
            name="fk_progress_check_in_application_roadmap",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "employee_identity_id", "roadmap_id", "id",
            name="uq_progress_check_in_employee_owner",
        ),
        UniqueConstraint(
            "machine_principal_id", "roadmap_id", "id",
            name="uq_progress_check_in_application_owner",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    employee_identity_id: Mapped[str | None] = mapped_column(String(64))
    machine_principal_id: Mapped[str | None] = mapped_column(String(64))
    roadmap_id: Mapped[str] = mapped_column(String(64), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    completed_step_references: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    normalized_milestone_keys: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    new_goals: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    idempotency_record_id: Mapped[str] = mapped_column(
        ForeignKey("idempotency_records.id"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ProgressReviewRecord(Base):
    __tablename__ = "progress_reviews"
    __table_args__ = (
        CheckConstraint(EXACT_OWNER, name="ck_progress_review_exact_owner"),
        ForeignKeyConstraint(
            ["employee_identity_id", "roadmap_id", "progress_check_in_id"],
            [
                "owned_progress_check_ins.employee_identity_id",
                "owned_progress_check_ins.roadmap_id",
                "owned_progress_check_ins.id",
            ],
            name="fk_progress_review_employee_check_in",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["machine_principal_id", "roadmap_id", "progress_check_in_id"],
            [
                "owned_progress_check_ins.machine_principal_id",
                "owned_progress_check_ins.roadmap_id",
                "owned_progress_check_ins.id",
            ],
            name="fk_progress_review_application_check_in",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    progress_check_in_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    roadmap_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    employee_identity_id: Mapped[str | None] = mapped_column(String(64))
    machine_principal_id: Mapped[str | None] = mapped_column(String(64))
    prior_roadmap_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_roadmap_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    current_status: Mapped[str] = mapped_column(String(128), nullable=False)
    gaps: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    milestone_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    next_action_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    next_action_target: Mapped[str] = mapped_column(String(256), nullable=False)
    next_action_reason: Mapped[str] = mapped_column(String(1024), nullable=False)
    next_action_title: Mapped[str] = mapped_column(String(512), nullable=False)
    presentation: Mapped[str] = mapped_column(Text, nullable=False)
    follow_up_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    contract_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


Index(
    "ix_progress_check_in_employee_latest",
    ProgressCheckInRecord.employee_identity_id,
    ProgressCheckInRecord.roadmap_id,
    ProgressCheckInRecord.created_at.desc(),
)
Index(
    "ix_progress_check_in_application_latest",
    ProgressCheckInRecord.machine_principal_id,
    ProgressCheckInRecord.roadmap_id,
    ProgressCheckInRecord.created_at.desc(),
)
Index(
    "ix_progress_review_employee_latest",
    ProgressReviewRecord.employee_identity_id,
    ProgressReviewRecord.roadmap_id,
    ProgressReviewRecord.created_at.desc(),
    ProgressReviewRecord.id,
)
Index(
    "ix_progress_review_application_latest",
    ProgressReviewRecord.machine_principal_id,
    ProgressReviewRecord.roadmap_id,
    ProgressReviewRecord.created_at.desc(),
    ProgressReviewRecord.id,
)
