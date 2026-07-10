"""Persistence operations for progress check-ins."""

from __future__ import annotations

from sqlalchemy import select

from knowledge.schemas import ProgressCheckIn
from storage.database import DatabaseManager, ProgressCheckInRecord


class ProgressRepository:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def save_check_in(self, check_in: ProgressCheckIn) -> ProgressCheckIn:
        payload = check_in.model_dump(mode="json")
        with self.database.session() as session:
            record = session.get(ProgressCheckInRecord, check_in.id)
            if record is None:
                record = ProgressCheckInRecord(
                    id=check_in.id,
                    employee_profile_id=check_in.employee_profile_id,
                    roadmap_id=check_in.roadmap_id,
                    payload=payload,
                    created_at=check_in.created_at,
                )
                session.add(record)
            else:
                record.employee_profile_id = check_in.employee_profile_id
                record.roadmap_id = check_in.roadmap_id
                record.payload = payload
        return check_in

    def get_latest_check_in(self, employee_profile_id: str) -> ProgressCheckIn | None:
        with self.database.session() as session:
            stmt = (
                select(ProgressCheckInRecord)
                .where(ProgressCheckInRecord.employee_profile_id == employee_profile_id)
                .order_by(ProgressCheckInRecord.created_at.desc())
            )
            record = session.execute(stmt).scalars().first()
            return ProgressCheckIn.model_validate(record.payload) if record else None

    def list_check_ins_for_roadmap(self, roadmap_id: str) -> list[ProgressCheckIn]:
        with self.database.session() as session:
            stmt = select(ProgressCheckInRecord).where(ProgressCheckInRecord.roadmap_id == roadmap_id)
            records = session.execute(stmt).scalars().all()
            return [ProgressCheckIn.model_validate(record.payload) for record in records]

