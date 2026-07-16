"""Persistence operations for employee profiles and roadmaps."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from knowledge.schemas import CareerRoadmap, EmployeeProfile
from storage.database import DatabaseManager, EmployeeProfileRecord, RoadmapRecord
from storage.roadmap_models import OwnedRoadmapRecord, RoadmapMilestoneRecord, stable_milestone_key


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RoadmapRepository:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def save_employee_profile(self, profile: EmployeeProfile) -> EmployeeProfile:
        now = utcnow()
        stored = profile.model_copy(update={"updated_at": now})
        payload = stored.model_dump(mode="json")
        with self.database.session() as session:
            record = session.get(EmployeeProfileRecord, stored.id)
            if record is None:
                record = EmployeeProfileRecord(
                    id=stored.id,
                    payload=payload,
                    created_at=stored.created_at,
                    updated_at=stored.updated_at,
                )
                session.add(record)
            else:
                record.payload = payload
                record.updated_at = stored.updated_at
        return stored

    def get_employee_profile(self, profile_id: str) -> EmployeeProfile | None:
        with self.database.session() as session:
            record = session.get(EmployeeProfileRecord, profile_id)
            return EmployeeProfile.model_validate(record.payload) if record else None

    def save_roadmap(self, roadmap: CareerRoadmap) -> CareerRoadmap:
        now = utcnow()
        stored = roadmap.model_copy(update={"updated_at": now})
        payload = stored.model_dump(mode="json")
        with self.database.session() as session:
            record = session.get(RoadmapRecord, stored.id)
            if record is None:
                record = RoadmapRecord(
                    id=stored.id,
                    employee_profile_id=stored.employee_profile_id,
                    status=stored.status,
                    payload=payload,
                    created_at=stored.created_at,
                    updated_at=stored.updated_at,
                )
                session.add(record)
            else:
                record.employee_profile_id = stored.employee_profile_id
                record.status = stored.status
                record.payload = payload
                record.updated_at = stored.updated_at
        return stored

    def get_roadmap(self, roadmap_id: str) -> CareerRoadmap | None:
        with self.database.session() as session:
            record = session.get(RoadmapRecord, roadmap_id)
            return CareerRoadmap.model_validate(record.payload) if record else None

    def get_latest_roadmap(self, employee_profile_id: str) -> CareerRoadmap | None:
        with self.database.session() as session:
            stmt = (
                select(RoadmapRecord)
                .where(RoadmapRecord.employee_profile_id == employee_profile_id)
                .order_by(RoadmapRecord.created_at.desc())
            )
            record = session.execute(stmt).scalars().first()
            return CareerRoadmap.model_validate(record.payload) if record else None

    def save_owned_roadmap(self, roadmap: CareerRoadmap, *, employee_identity_id: str | None = None, machine_principal_id: str | None = None) -> CareerRoadmap:
        owner_type = "employee" if employee_identity_id else "application"
        if (employee_identity_id is None) == (machine_principal_id is None):
            raise ValueError("exactly one roadmap owner is required")
        payload = roadmap.model_dump(mode="json")
        with self.database.session() as session:
            record = OwnedRoadmapRecord(
                id=roadmap.id, owner_type=owner_type, employee_identity_id=employee_identity_id,
                machine_principal_id=machine_principal_id, profile_snapshot={"roadmap": payload},
                goal=roadmap.goal_summary, status=str(roadmap.status), ui_contract_state="enriched",
                content_version="roadmap-v1", created_at=roadmap.created_at, updated_at=roadmap.updated_at,
            )
            session.add(record)
            for ordinal, milestone in enumerate(roadmap.milestones):
                session.add(RoadmapMilestoneRecord(
                    roadmap_id=roadmap.id, milestone_key=stable_milestone_key(milestone.title, ordinal),
                    ordinal=ordinal, title=milestone.title, status=str(milestone.completion_state),
                    created_at=roadmap.created_at,
                ))
        return roadmap

    def list_employee_owned(self, employee_identity_id: str) -> list[CareerRoadmap]:
        with self.database.session() as session:
            records = session.execute(select(OwnedRoadmapRecord).where(OwnedRoadmapRecord.employee_identity_id == employee_identity_id).order_by(OwnedRoadmapRecord.created_at.desc(), OwnedRoadmapRecord.id)).scalars()
            return [CareerRoadmap.model_validate(record.profile_snapshot["roadmap"]) for record in records if record.ui_contract_state == "enriched"]

    def get_employee_owned(self, roadmap_id: str, employee_identity_id: str) -> CareerRoadmap | None:
        with self.database.session() as session:
            record = session.execute(select(OwnedRoadmapRecord).where(OwnedRoadmapRecord.id == roadmap_id, OwnedRoadmapRecord.employee_identity_id == employee_identity_id)).scalar_one_or_none()
            if record is None:
                return None
            if record.ui_contract_state != "enriched":
                raise ValueError("LEGACY_RECORD_NOT_UI_COMPATIBLE")
            return CareerRoadmap.model_validate(record.profile_snapshot["roadmap"])
