from __future__ import annotations

from agent.contracts.progress import ProgressCheckInRequest
from agent.contracts.roadmap import RoadmapIntakeRequest
from knowledge.schemas import EmployeeProfile


def test_progress_service_creates_revised_roadmap_with_history(app_container):
    profile = EmployeeProfile(
        role="Linux admin",
        experience_level="intermediate",
        target_role="DevOps engineer",
        available_time_per_week=6,
        target_specializations=["Terraform"],
    )
    roadmap_response = app_container.roadmap_service.create_roadmap(RoadmapIntakeRequest(employee_profile=profile))
    assert roadmap_response.roadmap is not None
    roadmap = roadmap_response.roadmap
    completed_step = roadmap.milestones[0]

    response = app_container.progress_service.record_progress(
        ProgressCheckInRequest(
            employee_profile_id=roadmap.employee_profile_id,
            roadmap_id=roadmap.id,
            completed_steps=[completed_step.title],
            new_goals=["Kubernetes"],
            notes="Completed the first milestone",
        )
    )

    assert response.revision.prior_roadmap.id == roadmap.id
    assert response.revision.updated_roadmap.id != roadmap.id
    assert response.revision.updated_roadmap.previous_roadmap_id == roadmap.id
    assert response.revision.updated_roadmap.goal_summary != roadmap.goal_summary
    assert response.check_in is not None
    assert response.follow_up_prompt

