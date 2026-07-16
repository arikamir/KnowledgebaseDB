from agent.contracts.roadmap import RoadmapIntakeRequest
from knowledge.schemas import EmployeeProfile


def test_owned_create_list_get_and_cross_employee_denial(app_container):
    request = RoadmapIntakeRequest(employee_profile=EmployeeProfile(role="Administrator", experience_level="beginner", target_role="DevOps Engineer", available_time_per_week=5))
    result = app_container.roadmap_service.create_owned_roadmap(request, employee_identity_id="employee-a")
    assert result.roadmap is not None
    assert [item.id for item in app_container.roadmap_repository.list_employee_owned("employee-a")] == [result.roadmap.id]
    assert app_container.roadmap_repository.get_employee_owned(result.roadmap.id, "employee-a") is not None
    assert app_container.roadmap_repository.get_employee_owned(result.roadmap.id, "employee-b") is None
