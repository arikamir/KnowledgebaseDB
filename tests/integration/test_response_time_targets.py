from __future__ import annotations

from time import perf_counter


def test_response_time_targets_are_well_under_poc_limits(client):
    roadmap_start = perf_counter()
    roadmap_response = client.post(
        "/roadmaps",
        json={
            "employee_profile": {
                "role": "Linux admin",
                "experience_level": "intermediate",
                "target_role": "DevOps engineer",
                "available_time_per_week": 5,
            },
            "clarifying_questions_asked": 3,
        },
    )
    roadmap_elapsed = perf_counter() - roadmap_start

    skill_start = perf_counter()
    skill_response = client.post(
        "/skills/guidance",
        json={
            "topic": "Kubernetes",
            "employee_profile": {
                "role": "Platform engineer",
                "experience_level": "intermediate",
                "target_role": "Platform engineer",
                "available_time_per_week": 5,
            },
        },
    )
    skill_elapsed = perf_counter() - skill_start

    assert roadmap_response.status_code == 200
    assert skill_response.status_code == 200
    assert roadmap_elapsed < 1.0
    assert skill_elapsed < 1.0

