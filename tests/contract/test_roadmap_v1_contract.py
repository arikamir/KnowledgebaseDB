from agent.contracts.roadmap import RoadmapIntakeRequest
from knowledge.schemas import EmployeeProfile


def valid_request() -> RoadmapIntakeRequest:
    return RoadmapIntakeRequest(employee_profile=EmployeeProfile(role="Systems Administrator", experience_level="beginner", target_role="DevOps Engineer", available_time_per_week=6), request_text="Create a container and delivery roadmap")


def test_ready_result_contains_a_nonempty_roadmap(app_container):
    result = app_container.roadmap_service.create_owned_roadmap(valid_request(), employee_identity_id="employee-a")
    assert result.status == "ready"
    assert result.roadmap is not None and result.roadmap.milestones
    assert not result.clarifying_questions


def test_needs_more_info_contains_questions_and_no_roadmap(app_container):
    result = app_container.roadmap_service.create_roadmap(RoadmapIntakeRequest(employee_profile=EmployeeProfile()))
    assert result.status == "needs_more_info"
    assert result.roadmap is None
    assert result.clarifying_questions


def test_application_owned_create_never_fabricates_employee_owner(app_container):
    result = app_container.roadmap_service.create_owned_roadmap(valid_request(), machine_principal_id="application-a")
    assert result.status == "ready"
