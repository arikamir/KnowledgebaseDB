"""Foundation-owned roadmap ownership and stable milestone records."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from storage.database import Base, utcnow


class OwnedRoadmapRecord(Base):
    __tablename__ = "owned_roadmaps"
    __table_args__ = (
        CheckConstraint("(owner_type = 'employee' AND employee_identity_id IS NOT NULL AND machine_principal_id IS NULL) OR (owner_type = 'application' AND machine_principal_id IS NOT NULL AND employee_identity_id IS NULL)", name="ck_roadmap_exact_owner"),
        UniqueConstraint("employee_identity_id", "id", name="uq_employee_roadmap"),
        UniqueConstraint("machine_principal_id", "id", name="uq_application_roadmap"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(16), nullable=False)
    employee_identity_id: Mapped[str | None] = mapped_column(ForeignKey("employee_identities.id", ondelete="CASCADE"))
    machine_principal_id: Mapped[str | None] = mapped_column(ForeignKey("machine_principals.id", ondelete="CASCADE"))
    profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    goal: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    ui_contract_state: Mapped[str] = mapped_column(String(16), default="enriched", nullable=False)
    content_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RoadmapMilestoneRecord(Base):
    __tablename__ = "roadmap_milestones"
    __table_args__ = (
        UniqueConstraint("roadmap_id", "milestone_key", name="uq_roadmap_milestone_key"),
        UniqueConstraint("roadmap_id", "ordinal", name="uq_roadmap_milestone_ordinal"),
    )
    roadmap_id: Mapped[str] = mapped_column(ForeignKey("owned_roadmaps.id", ondelete="CASCADE"), primary_key=True)
    milestone_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
