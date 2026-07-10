from __future__ import annotations

from agent.contracts.roadmap import RoadmapIntakeRequest
from knowledge.schemas import EmployeeProfile


def test_roadmap_service_asks_no_more_than_three_questions(app_container):
    request = RoadmapIntakeRequest(employee_profile=EmployeeProfile())

    response = app_container.roadmap_service.create_roadmap(request)

    assert response.status == "needs_more_info"
    assert len(response.clarifying_questions) <= 3
    assert response.roadmap is None


def test_roadmap_service_builds_complete_roadmap_with_required_fields(app_container):
    profile = EmployeeProfile(
        role="Windows administrator",
        experience_level="beginner",
        target_role="DevOps engineer",
        target_specializations=["Kubernetes", "Azure DevOps"],
        available_time_per_week=5,
        learning_preferences=["hands-on"],
    )
    request = RoadmapIntakeRequest(employee_profile=profile, clarifying_questions_asked=0)

    response = app_container.roadmap_service.create_roadmap(request)

    assert response.status == "ready"
    assert response.roadmap is not None
    roadmap = response.roadmap
    assert len(roadmap.milestones) == 3
    assert roadmap.current_focus
    assert roadmap.goal_summary.startswith("Move from")
    for step in roadmap.milestones:
        assert step.skill_area
        assert step.experience_level_fit
        assert step.concrete_next_action
        assert step.reason_it_matters


def test_roadmap_service_falls_back_with_assumptions_after_three_questions(app_container):
    profile = EmployeeProfile(role=None, experience_level=None, target_role=None, available_time_per_week=None)
    request = RoadmapIntakeRequest(employee_profile=profile, clarifying_questions_asked=3)

    response = app_container.roadmap_service.create_roadmap(request)

    assert response.status == "ready"
    assert response.roadmap is not None
    assert response.assumptions
    assert response.follow_up_prompt
    assert response.presentation

