"""Persistence operations for progress check-ins."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from knowledge.schemas import CareerRoadmap, ProgressCheckIn
from storage.database import DatabaseManager, ProgressCheckInRecord as LegacyProgressCheckInRecord, utcnow
from storage.progress_models import ProgressCheckInRecord, ProgressReviewRecord
from storage.roadmap_models import OwnedRoadmapRecord, RoadmapMilestoneRecord


class ProgressRoadmapNotFound(RuntimeError):
    pass


class RoadmapVersionConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class OwnedRoadmapContext:
    roadmap: CareerRoadmap
    expected_updated_at: datetime


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


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

    def get_owned_roadmap_context(
        self,
        roadmap_id: str,
        *,
        employee_identity_id: str | None = None,
        machine_principal_id: str | None = None,
    ) -> OwnedRoadmapContext:
        if (employee_identity_id is None) == (machine_principal_id is None):
            raise ValueError("exactly one progress owner is required")
        with self.database.session() as session:
            owner_filter = (
                OwnedRoadmapRecord.employee_identity_id == employee_identity_id
                if employee_identity_id is not None
                else OwnedRoadmapRecord.machine_principal_id == machine_principal_id
            )
            record = session.execute(
                select(OwnedRoadmapRecord).where(
                    OwnedRoadmapRecord.id == roadmap_id,
                    owner_filter,
                )
            ).scalar_one_or_none()
            if record is None:
                raise ProgressRoadmapNotFound("ROADMAP_NOT_FOUND")
            if record.ui_contract_state != "enriched":
                raise ValueError("LEGACY_RECORD_NOT_UI_COMPATIBLE")
            roadmap = CareerRoadmap.model_validate(record.profile_snapshot["roadmap"])
            stored_milestones = session.execute(
                select(RoadmapMilestoneRecord)
                .where(RoadmapMilestoneRecord.roadmap_id == roadmap_id)
                .order_by(RoadmapMilestoneRecord.ordinal, RoadmapMilestoneRecord.milestone_key)
            ).scalars().all()
            by_ordinal = {item.ordinal: item for item in stored_milestones}
            milestones = []
            for ordinal, milestone in enumerate(roadmap.milestones):
                stored = by_ordinal.get(ordinal)
                if stored is None:
                    raise ValueError("LEGACY_RECORD_NOT_UI_COMPATIBLE")
                milestones.append(milestone.model_copy(update={
                    "milestone_key": stored.milestone_key,
                    "ordinal": stored.ordinal,
                    "completion_state": stored.status,
                }))
            enriched_by_id = {item.id: item for item in milestones}
            enriched = roadmap.model_copy(update={
                "owner_type": record.owner_type,
                "milestones": milestones,
                "next_actions": [
                    enriched_by_id.get(item.id, item) for item in roadmap.next_actions
                ],
            })
            return OwnedRoadmapContext(enriched, record.updated_at)

    def commit_owned_review(
        self,
        *,
        expected_updated_at: datetime,
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
        """Atomically revise the owned roadmap and append its check-in/review."""
        self._validate_owner(actor_type, employee_identity_id, machine_principal_id)
        timestamp = created_at or utcnow()
        owner_filter = (
            OwnedRoadmapRecord.employee_identity_id == employee_identity_id
            if employee_identity_id is not None
            else OwnedRoadmapRecord.machine_principal_id == machine_principal_id
        )
        with self.database.session() as session:
            result = session.execute(
                update(OwnedRoadmapRecord)
                .where(
                    OwnedRoadmapRecord.id == roadmap_id,
                    owner_filter,
                    OwnedRoadmapRecord.updated_at == expected_updated_at,
                )
                .values(
                    profile_snapshot={"roadmap": updated_roadmap_snapshot},
                    goal=updated_roadmap_snapshot["goal_summary"],
                    status=updated_roadmap_snapshot["status"],
                    updated_at=timestamp,
                )
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise RoadmapVersionConflict("ROADMAP_VERSION_CONFLICT")

            for item in milestone_snapshot:
                milestone_key = item.get("milestone_key")
                ordinal = item.get("ordinal")
                if not isinstance(milestone_key, str) or not isinstance(ordinal, int):
                    raise ValueError("owned milestone identity is required")
                stored = session.get(RoadmapMilestoneRecord, (roadmap_id, milestone_key))
                if stored is None:
                    session.add(RoadmapMilestoneRecord(
                        roadmap_id=roadmap_id,
                        milestone_key=milestone_key,
                        ordinal=ordinal,
                        title=item["title"],
                        status=item["completion_state"],
                        created_at=timestamp,
                        completed_at=(timestamp if item["completion_state"] == "completed" else None),
                    ))
                else:
                    stored.ordinal = ordinal
                    stored.title = item["title"]
                    stored.status = item["completion_state"]
                    if item["completion_state"] == "completed" and stored.completed_at is None:
                        stored.completed_at = timestamp

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
            session.flush()
            return self._review_payload(review, check_in)

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
        updated_recommendations = [
            item for item in review.milestone_snapshot
            if item.get("completion_state") != "completed"
        ] or list(review.milestone_snapshot)
        summary_parts = []
        if check_in.completed_step_references:
            summary_parts.append(
                f"Marked completed: {', '.join(check_in.completed_step_references)}"
            )
        if check_in.new_goals:
            summary_parts.append(f"Added goals: {', '.join(check_in.new_goals)}")
        return {
            "revision": {
                "prior_roadmap": review.prior_roadmap_snapshot,
                "updated_roadmap": review.updated_roadmap_snapshot,
                "completed_steps": check_in.completed_step_references,
                "normalized_milestone_keys": check_in.normalized_milestone_keys,
                "new_goals": check_in.new_goals,
                "summary": "; ".join(summary_parts) or "Progress check-in recorded.",
                "created_at": _aware(review.created_at),
            },
            "presentation": review.presentation,
            "follow_up_prompt": review.follow_up_prompt,
            "roadmap_id": review.roadmap_id,
            "current_status": review.current_status,
            "gaps": review.gaps,
            "milestones": review.milestone_snapshot,
            "next_action": {
                "kind": review.next_action_kind,
                "title": review.next_action_title,
                "target": review.next_action_target,
                "reason": review.next_action_reason,
            },
            "check_in": {
                "id": check_in.id,
                "owner_type": check_in.actor_type,
                "employee_profile_id": review.updated_roadmap_snapshot["employee_profile_id"],
                "roadmap_id": check_in.roadmap_id,
                "notes": check_in.notes,
                "completed_steps": check_in.completed_step_references,
                "normalized_milestone_keys": check_in.normalized_milestone_keys,
                "new_goals": check_in.new_goals,
                "updated_recommendations": updated_recommendations,
                "created_at": _aware(check_in.created_at),
            },
        }
