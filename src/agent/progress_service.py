"""Roadmap revision logic based on employee progress check-ins."""

from __future__ import annotations

from dataclasses import dataclass

from agent.contracts.progress import ProgressCheckInRequest, ProgressReviewResponse
from agent.roadmap_presenter import present_roadmap
from agent.roadmap_revision import RoadmapRevision
from agent.roadmap_service import RoadmapService
from knowledge.schemas import CompletionState, EmployeeProfile, ProgressCheckIn, RoadmapStatus, enum_text, make_id, utcnow
from storage.progress_repository import ProgressRepository
from storage.roadmap_repository import RoadmapRepository


@dataclass(slots=True)
class ProgressService:
    roadmap_repository: RoadmapRepository
    progress_repository: ProgressRepository
    roadmap_service: RoadmapService

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
            employee_profile_id=request.employee_profile_id,
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
