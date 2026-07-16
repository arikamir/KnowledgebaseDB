"""Roadmap revision logic based on employee progress check-ins."""

from __future__ import annotations

from dataclasses import dataclass

from agent.contracts.progress import ProgressCheckInRequest, ProgressReviewResponse
from agent.next_action import MilestoneCandidate, select_next_action
from agent.roadmap_presenter import present_roadmap
from agent.roadmap_revision import RoadmapRevision
from agent.roadmap_service import RoadmapService
from knowledge.schemas import CompletionState, EmployeeProfile, ProgressCheckIn, RoadmapStatus, enum_text, make_id, utcnow
from storage.progress_repository import (
    OwnedRoadmapContext,
    ProgressRepository,
    RoadmapVersionConflict,
)
from storage.roadmap_models import stable_milestone_key
from storage.roadmap_repository import RoadmapRepository


@dataclass(slots=True)
class ProgressService:
    roadmap_repository: RoadmapRepository
    progress_repository: ProgressRepository
    roadmap_service: RoadmapService

    def record_owned_progress(
        self,
        request: ProgressCheckInRequest,
        *,
        actor_type: str,
        actor_id: str,
        idempotency_record_id: str,
    ) -> ProgressReviewResponse:
        owner = (
            {"employee_identity_id": actor_id}
            if actor_type == "employee"
            else {"machine_principal_id": actor_id}
        )
        check_in_id = make_id()
        review_id = make_id()
        for attempt in range(2):
            context = self.progress_repository.get_owned_roadmap_context(
                request.roadmap_id,
                **owner,
            )
            response = self._evaluate_owned_progress(
                context,
                request,
                actor_type=actor_type,
                check_in_id=check_in_id,
            )
            try:
                self.progress_repository.commit_owned_review(
                    expected_updated_at=context.expected_updated_at,
                    check_in_id=check_in_id,
                    review_id=review_id,
                    actor_type=actor_type,
                    roadmap_id=request.roadmap_id,
                    idempotency_record_id=idempotency_record_id,
                    notes=request.notes,
                    completed_step_references=request.completed_steps,
                    normalized_milestone_keys=response.revision.normalized_milestone_keys,
                    new_goals=request.new_goals,
                    prior_roadmap_snapshot=response.revision.prior_roadmap.model_dump(mode="json"),
                    updated_roadmap_snapshot=response.revision.updated_roadmap.model_dump(mode="json"),
                    current_status=response.current_status,
                    gaps=response.gaps,
                    milestone_snapshot=[item.model_dump(mode="json") for item in response.milestones],
                    next_action=response.next_action.model_dump(mode="json"),
                    presentation=response.presentation,
                    follow_up_prompt=response.follow_up_prompt,
                    created_at=response.check_in.created_at if response.check_in else None,
                    **owner,
                )
                return response
            except RoadmapVersionConflict:
                if attempt == 1:
                    raise
        raise RoadmapVersionConflict("ROADMAP_VERSION_CONFLICT")

    def restore_owned_review(
        self,
        roadmap_id: str,
        *,
        employee_identity_id: str,
    ) -> ProgressReviewResponse | None:
        payload = self.progress_repository.get_latest_owned_review(
            roadmap_id,
            employee_identity_id=employee_identity_id,
        )
        return ProgressReviewResponse.model_validate(payload) if payload else None

    def _evaluate_owned_progress(
        self,
        context: OwnedRoadmapContext,
        request: ProgressCheckInRequest,
        *,
        actor_type: str,
        check_in_id: str,
    ) -> ProgressReviewResponse:
        roadmap = context.roadmap
        by_key = {
            item.milestone_key: item
            for item in roadmap.milestones
            if item.milestone_key is not None
        }
        unknown_keys = [
            key for key in request.completed_milestone_keys if key not in by_key
        ]
        if unknown_keys:
            raise ValueError(f"MILESTONE_KEY_UNKNOWN:{','.join(unknown_keys)}")

        normalized_keys = list(request.completed_milestone_keys)
        legacy_terms = {item.casefold() for item in request.completed_steps}
        for milestone in roadmap.milestones:
            if (
                milestone.title.casefold() in legacy_terms
                or milestone.skill_area.casefold() in legacy_terms
            ) and milestone.milestone_key not in normalized_keys:
                if milestone.milestone_key is not None:
                    normalized_keys.append(milestone.milestone_key)

        updated_milestones = [
            milestone.model_copy(update={"completion_state": CompletionState.COMPLETED})
            if milestone.milestone_key in normalized_keys
            else milestone
            for milestone in roadmap.milestones
        ]
        profile = self.roadmap_repository.get_employee_profile(roadmap.employee_profile_id)
        if profile is None:
            profile = EmployeeProfile(id=roadmap.employee_profile_id)
        new_steps = self.roadmap_service.suggest_steps_for_goals(
            profile=profile,
            goals=request.new_goals,
            starting_priority=len(updated_milestones) + 1,
        ) if request.new_goals else []
        for ordinal, step in enumerate(new_steps, start=len(updated_milestones)):
            updated_milestones.append(step.model_copy(update={
                "milestone_key": stable_milestone_key(step.title, ordinal),
                "ordinal": ordinal,
            }))

        remaining = [
            item for item in updated_milestones
            if enum_text(item.completion_state) != CompletionState.COMPLETED.value
        ]
        timestamp = utcnow()
        status = RoadmapStatus.REVISED if remaining else RoadmapStatus.COMPLETED
        updated_roadmap = roadmap.model_copy(update={
            "owner_type": actor_type,
            "goal_summary": self._updated_goal_summary(roadmap.goal_summary, request.new_goals),
            "current_focus": remaining[0].title if remaining else roadmap.current_focus,
            "milestones": updated_milestones,
            "next_actions": remaining[:2] if remaining else roadmap.next_actions,
            "status": status,
            "updated_at": timestamp,
        })
        selected = select_next_action(
            roadmap.id,
            [
                MilestoneCandidate(
                    roadmap_id=roadmap.id,
                    milestone_key=item.milestone_key or stable_milestone_key(item.title, ordinal),
                    ordinal=item.ordinal if item.ordinal is not None else ordinal,
                    title=item.title,
                    completed=enum_text(item.completion_state) == CompletionState.COMPLETED.value,
                )
                for ordinal, item in enumerate(updated_milestones)
            ],
        )
        next_action = {
            "kind": selected.action_type,
            "title": selected.title,
            "reason": (
                "Continue the next incomplete milestone."
                if selected.action_type == "continue_milestone"
                else "All milestones are complete; review or refresh the roadmap."
            ),
            "target": selected.milestone_key or selected.roadmap_id,
        }
        check_in = ProgressCheckIn(
            id=check_in_id,
            owner_type=actor_type,
            employee_profile_id=roadmap.employee_profile_id,
            roadmap_id=roadmap.id,
            notes=request.notes,
            completed_steps=request.completed_steps,
            normalized_milestone_keys=normalized_keys,
            new_goals=request.new_goals,
            updated_recommendations=remaining or updated_milestones,
            created_at=timestamp,
        )
        presentation = present_roadmap(updated_roadmap)
        return ProgressReviewResponse(
            revision=RoadmapRevision(
                prior_roadmap=roadmap,
                updated_roadmap=updated_roadmap,
                completed_steps=request.completed_steps,
                normalized_milestone_keys=normalized_keys,
                new_goals=request.new_goals,
                summary=self._summary(request.completed_steps, request.new_goals),
                created_at=timestamp,
            ),
            presentation=presentation.text,
            follow_up_prompt=presentation.follow_up_prompt,
            check_in=check_in,
            roadmap_id=roadmap.id,
            current_status="in_progress" if remaining else "completed",
            gaps=[item.title for item in remaining],
            milestones=updated_milestones,
            next_action=next_action,
        )

    def record_progress(self, request: ProgressCheckInRequest) -> ProgressReviewResponse:
        roadmap = self.roadmap_repository.get_roadmap(request.roadmap_id)
        if roadmap is None:
            raise ValueError("Roadmap not found for the supplied roadmap_id")

        completed = {step.strip().lower() for step in request.completed_steps}
        prior_roadmap = roadmap.model_copy(deep=True)

        updated_steps = []
        for step in roadmap.milestones:
            if step.title.lower() in completed or step.skill_area.lower() in completed:
                updated_steps.append(step.model_copy(update={"completion_state": CompletionState.COMPLETED}))
            else:
                updated_steps.append(step)

        profile = self.roadmap_repository.get_employee_profile(roadmap.employee_profile_id) or EmployeeProfile(
            id=roadmap.employee_profile_id
        )
        new_goal_steps = self.roadmap_service.suggest_steps_for_goals(
            profile=profile,
            goals=request.new_goals,
            starting_priority=len(updated_steps) + 1,
        ) if request.new_goals else []

        remaining_steps = [
            step for step in updated_steps if enum_text(step.completion_state) != CompletionState.COMPLETED.value
        ]
        merged_steps = remaining_steps + new_goal_steps
        if not merged_steps:
            merged_steps = updated_steps

        updated_roadmap = roadmap.model_copy(
            update={
                "id": make_id(),
                "previous_roadmap_id": roadmap.id,
                "goal_summary": self._updated_goal_summary(roadmap.goal_summary, request.new_goals),
                "current_focus": merged_steps[0].title if merged_steps else roadmap.current_focus,
                "milestones": updated_steps + new_goal_steps,
                "next_actions": merged_steps[:2] if merged_steps else roadmap.next_actions,
                "status": RoadmapStatus.REVISED,
                "created_at": utcnow(),
                "updated_at": utcnow(),
            }
        )

        check_in = ProgressCheckIn(
            employee_profile_id=request.employee_profile_id or roadmap.employee_profile_id,
            roadmap_id=request.roadmap_id,
            notes=request.notes,
            completed_steps=request.completed_steps,
            new_goals=request.new_goals,
            updated_recommendations=merged_steps,
        )
        self.progress_repository.save_check_in(check_in)
        saved_roadmap = self.roadmap_repository.save_roadmap(updated_roadmap)
        revision = RoadmapRevision(
            prior_roadmap=prior_roadmap,
            updated_roadmap=saved_roadmap,
            completed_steps=request.completed_steps,
            new_goals=request.new_goals,
            summary=self._summary(completed=request.completed_steps, goals=request.new_goals),
        )
        presentation = present_roadmap(saved_roadmap)
        return ProgressReviewResponse(
            revision=revision,
            presentation=presentation.text,
            follow_up_prompt=presentation.follow_up_prompt,
            check_in=check_in,
            roadmap_id=saved_roadmap.id,
            current_status="in_progress" if merged_steps else "completed",
            gaps=[item.title for item in merged_steps],
            milestones=saved_roadmap.milestones,
            next_action={
                "kind": "continue_milestone" if merged_steps else "review_roadmap",
                "title": merged_steps[0].title if merged_steps else "Review your completed roadmap",
                "reason": (
                    "Continue the next incomplete milestone."
                    if merged_steps
                    else "All milestones are complete; review or refresh the roadmap."
                ),
                "target": saved_roadmap.id,
            },
        )

    def _updated_goal_summary(self, goal_summary: str, new_goals: list[str]) -> str:
        if not new_goals:
            return goal_summary
        return f"{goal_summary} | Updated goals: {', '.join(new_goals)}"

    def _summary(self, completed: list[str], goals: list[str]) -> str:
        parts = []
        if completed:
            parts.append(f"Marked completed: {', '.join(completed)}")
        if goals:
            parts.append(f"Added goals: {', '.join(goals)}")
        return "; ".join(parts) if parts else "Progress check-in recorded."
