"""Persistence operations for employee profiles and roadmaps."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from knowledge.schemas import CareerRoadmap, EmployeeProfile
from storage.database import DatabaseManager, EmployeeProfileRecord, RoadmapRecord


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

