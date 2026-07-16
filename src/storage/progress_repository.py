"""Persistence operations for progress check-ins."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from knowledge.schemas import ProgressCheckIn
from storage.database import DatabaseManager, ProgressCheckInRecord as LegacyProgressCheckInRecord, utcnow
from storage.progress_models import ProgressCheckInRecord, ProgressReviewRecord


class ProgressRepository:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def save_check_in(self, check_in: ProgressCheckIn) -> ProgressCheckIn:
        payload = check_in.model_dump(mode="json")
        with self.database.session() as session:
            record = session.get(LegacyProgressCheckInRecord, check_in.id)
            if record is None:
                record = LegacyProgressCheckInRecord(
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
                select(LegacyProgressCheckInRecord)
                .where(LegacyProgressCheckInRecord.employee_profile_id == employee_profile_id)
                .order_by(LegacyProgressCheckInRecord.created_at.desc())
            )
            record = session.execute(stmt).scalars().first()
            return ProgressCheckIn.model_validate(record.payload) if record else None

    def list_check_ins_for_roadmap(self, roadmap_id: str) -> list[ProgressCheckIn]:
        with self.database.session() as session:
            stmt = select(LegacyProgressCheckInRecord).where(LegacyProgressCheckInRecord.roadmap_id == roadmap_id)
            records = session.execute(stmt).scalars().all()
            return [ProgressCheckIn.model_validate(record.payload) for record in records]

    def save_owned_review(
        self,
        *,
        check_in_id: str,
        review_id: str,
        actor_type: str,
        roadmap_id: str,
        idempotency_record_id: str,
        notes: str,
        completed_step_references: list[str],
        normalized_milestone_keys: list[str],
        new_goals: list[str],
        prior_roadmap_snapshot: dict[str, Any],
        updated_roadmap_snapshot: dict[str, Any],
        current_status: str,
        gaps: list[str],
        milestone_snapshot: list[dict[str, Any]],
        next_action: dict[str, str],
        presentation: str,
        follow_up_prompt: str,
        employee_identity_id: str | None = None,
        machine_principal_id: str | None = None,
        created_at: datetime | None = None,
        contract_version: str = "1.0.0",
    ) -> dict[str, Any]:
        """Persist one append-only check-in and its immutable review atomically."""
        self._validate_owner(actor_type, employee_identity_id, machine_principal_id)
        timestamp = created_at or utcnow()
        with self.database.session() as session:
            check_in = ProgressCheckInRecord(
                id=check_in_id,
                actor_type=actor_type,
                employee_identity_id=employee_identity_id,
                machine_principal_id=machine_principal_id,
                roadmap_id=roadmap_id,
                notes=notes,
                completed_step_references=list(completed_step_references),
                normalized_milestone_keys=list(normalized_milestone_keys),
                new_goals=list(new_goals),
                idempotency_record_id=idempotency_record_id,
                created_at=timestamp,
            )
            review = ProgressReviewRecord(
                id=review_id,
                progress_check_in_id=check_in_id,
                roadmap_id=roadmap_id,
                actor_type=actor_type,
                employee_identity_id=employee_identity_id,
                machine_principal_id=machine_principal_id,
                prior_roadmap_snapshot=prior_roadmap_snapshot,
                updated_roadmap_snapshot=updated_roadmap_snapshot,
                current_status=current_status,
                gaps=list(gaps),
                milestone_snapshot=list(milestone_snapshot),
                next_action_kind=next_action["kind"],
                next_action_title=next_action["title"],
                next_action_target=next_action["target"],
                next_action_reason=next_action["reason"],
                presentation=presentation,
                follow_up_prompt=follow_up_prompt,
                contract_version=contract_version,
                created_at=timestamp,
            )
            session.add_all((check_in, review))
        return self._review_payload(review, check_in)

    def get_latest_owned_review(
        self,
        roadmap_id: str,
        *,
        employee_identity_id: str | None = None,
        machine_principal_id: str | None = None,
    ) -> dict[str, Any] | None:
        if (employee_identity_id is None) == (machine_principal_id is None):
            raise ValueError("exactly one progress owner is required")
        with self.database.session() as session:
            owner_filter = (
                ProgressReviewRecord.employee_identity_id == employee_identity_id
                if employee_identity_id is not None
                else ProgressReviewRecord.machine_principal_id == machine_principal_id
            )
            review = session.execute(
                select(ProgressReviewRecord)
                .where(ProgressReviewRecord.roadmap_id == roadmap_id, owner_filter)
                .order_by(ProgressReviewRecord.created_at.desc(), ProgressReviewRecord.id)
            ).scalars().first()
            if review is None:
                return None
            check_in = session.get(ProgressCheckInRecord, review.progress_check_in_id)
            if check_in is None:  # Protected by the database FK; defensive for corrupt fixtures.
                raise RuntimeError("PROGRESS_CHECK_IN_MISSING")
            return self._review_payload(review, check_in)

    @staticmethod
    def _validate_owner(
        actor_type: str,
        employee_identity_id: str | None,
        machine_principal_id: str | None,
    ) -> None:
        if actor_type == "employee" and employee_identity_id and machine_principal_id is None:
            return
        if actor_type == "application" and machine_principal_id and employee_identity_id is None:
            return
        raise ValueError("exactly one progress owner matching actor_type is required")

    @staticmethod
    def _review_payload(
        review: ProgressReviewRecord,
        check_in: ProgressCheckInRecord,
    ) -> dict[str, Any]:
        return {
            "id": review.id,
            "roadmap_id": review.roadmap_id,
            "actor_type": review.actor_type,
            "check_in": {
                "id": check_in.id,
                "actor_type": check_in.actor_type,
                "roadmap_id": check_in.roadmap_id,
                "notes": check_in.notes,
                "completed_steps": check_in.completed_step_references,
                "normalized_milestone_keys": check_in.normalized_milestone_keys,
                "new_goals": check_in.new_goals,
                "created_at": check_in.created_at,
            },
            "prior_roadmap_snapshot": review.prior_roadmap_snapshot,
            "updated_roadmap_snapshot": review.updated_roadmap_snapshot,
            "current_status": review.current_status,
            "gaps": review.gaps,
            "milestones": review.milestone_snapshot,
            "next_action": {
                "kind": review.next_action_kind,
                "title": review.next_action_title,
                "target": review.next_action_target,
                "reason": review.next_action_reason,
            },
            "presentation": review.presentation,
            "follow_up_prompt": review.follow_up_prompt,
            "contract_version": review.contract_version,
            "created_at": review.created_at,
        }
